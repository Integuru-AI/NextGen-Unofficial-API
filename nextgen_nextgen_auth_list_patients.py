from curl_cffi import requests
import re
from html import unescape


def run(headers, user_input):
    """Search and list patients from HealthFusion. Returns patient demographics including chart number, name, DOB, insurance, and account status."""

    # Get optional search parameters
    search_type = user_input.get("search_type", "Patient")
    search_by = user_input.get("search_by", "name")
    query = user_input.get("query", "")

    # Validate search_type
    valid_search_types = ["Patient", "Insured", "Guarantor", "All", "NewPatient"]
    if search_type not in valid_search_types:
        return {'status_code': 400, 'body': {'error': f'Invalid search_type. Must be one of: {valid_search_types}'}}

    # Validate search_by
    valid_search_by = ["name", "dob", "phone", "ssn", "chart"]
    if search_by not in valid_search_by:
        return {'status_code': 400, 'body': {'error': f'Invalid search_by. Must be one of: {valid_search_by}'}}

    # Map search_by to the corresponding hidden field
    field_mapping = {
        "name": "PATIENT_NAME",
        "dob": "DOB",
        "phone": "HOME_PHONE",
        "ssn": "SSN",
        "chart": "PATIENT_ACCOUNT_NO"
    }

    # Build form data - all filter fields start empty, only the selected one gets the query
    form_data = {
        "SEARCH_TYPE": search_type,
        "hdrSearchType": search_by,
        "txtQry": query,
        "submitButton": "Search",
        "ACTION_NAME_PATIENT": "",
        "ACTION_NAME": "PATIENT_VIEW_DATA",
        "PATIENT_NAME": "",
        "DOB": "",
        "HOME_PHONE": "",
        "SSN": "",
        "PATIENT_ACCOUNT_NO": "",
        "MULTI_RESOURCE_IDS": "",
        "APPT_TYPE": "",
        "LOCATION_ID": "",
        "CALENDAR_RESOURCE_ID": "",
        "CURRENT_DATE": "",
        "APPOINTMENT_ID": "",
        "LAB_ID": ""
    }

    # Set the appropriate filter field based on search_by
    if query:
        form_data[field_mapping[search_by]] = query

    try:
        response = _call_api(form_data, headers)
    except Exception as e:
        return {'status_code': 500, 'body': {'error': str(e)}}

    # Check for session expiration (login page redirect)
    if "login" in response.url.lower() or "j_security_check" in response.text.lower():
        return {'status_code': 401, 'body': {'error': 'Session expired'}}

    if response.status_code != 200:
        return {'status_code': response.status_code, 'body': {'error': 'Request failed'}}

    # Parse HTML response to extract patients
    patients = _parse_patients(response.text)

    return {
        'status_code': 200,
        'body': {
            'patients': patients,
            'count': len(patients)
        }
    }

# === PRIVATE ===

def _call_api(form_data, headers):
    """POST patient search form to HealthFusion."""
    return requests.post(
        f"{BASE_URL}/electronic/pm/action.do",
        data=form_data,
        headers={
            **headers,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/electronic/pm/action.do?ACTION_NAME=PATIENT_VIEW_DATA"
        },
        impersonate="chrome131",
        timeout=30
    )


def _parse_patients(html):
    """Parse HTML response and extract patient records."""
    patients = []

    # Pattern to match table rows with patient data
    row_pattern = re.compile(
        r"<tr[^>]*>.*?submit_option\('PATIENT_CHARGE_ENTRY_ACTION',\s*'(\d+)'\).*?>(HF\d+)</a>.*?"
        r"<td[^>]*>([^<]*)</td>.*?"  # Patient Name
        r"<td[^>]*>([^<]*)</td>.*?"  # DOB
        r"<td[^>]*>([^<]*)</td>.*?"  # SSN
        r"<td[^>]*>([^<]*)</td>.*?"  # Home Phone
        r"<td[^>]*>([^<]*)</td>.*?"  # Primary Insurance
        r"<td[^>]*>([^<]*)</td>.*?"  # Insured ID
        r"<td[^>]*>.*?<span[^>]*>([^<]*)</span>.*?</td>",  # Account Status
        re.DOTALL | re.IGNORECASE
    )

    for match in row_pattern.finditer(html):
        member_id, chart_number, name, dob, ssn, phone, insurance, insured_id, status = match.groups()
        patients.append({
            "member_id": member_id.strip(),
            "chart_number": chart_number.strip(),
            "name": unescape(name.strip()),
            "dob": dob.strip(),
            "ssn": ssn.strip(),
            "home_phone": phone.strip(),
            "primary_insurance": unescape(insurance.strip()),
            "insured_id": insured_id.strip(),
            "account_status": status.strip()
        })

    # If regex didn't match, try a simpler approach
    if not patients:
        chart_pattern = re.compile(
            r"submit_option\('PATIENT_CHARGE_ENTRY_ACTION',\s*'(\d+)'\)[^>]*>(HF\d+)</a>",
            re.IGNORECASE
        )

        chart_matches = list(chart_pattern.finditer(html))

        if chart_matches:
            table_match = re.search(r'<table[^>]*class="[^"]*dataTable[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
            if table_match:
                table_html = table_match.group(1)
                row_matches = re.findall(r'<tr[^>]*class="[^"]*(?:odd|even)[^"]*"[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)

                for row_html in row_matches:
                    chart_match = re.search(r"submit_option\('PATIENT_CHARGE_ENTRY_ACTION',\s*'(\d+)'\)[^>]*>(HF\d+)</a>", row_html, re.IGNORECASE)
                    if chart_match:
                        member_id = chart_match.group(1)
                        chart_number = chart_match.group(2)

                        tds = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL | re.IGNORECASE)

                        if len(tds) >= 8:
                            def clean_cell(cell):
                                text = re.sub(r'<[^>]+>', '', cell)
                                text = unescape(text)
                                return ' '.join(text.split())

                            patients.append({
                                "member_id": member_id,
                                "chart_number": chart_number,
                                "name": clean_cell(tds[1]) if len(tds) > 1 else "",
                                "dob": clean_cell(tds[2]) if len(tds) > 2 else "",
                                "ssn": clean_cell(tds[3]) if len(tds) > 3 else "",
                                "home_phone": clean_cell(tds[4]) if len(tds) > 4 else "",
                                "primary_insurance": clean_cell(tds[5]) if len(tds) > 5 else "",
                                "insured_id": clean_cell(tds[6]) if len(tds) > 6 else "",
                                "account_status": clean_cell(tds[7]) if len(tds) > 7 else ""
                            })

    return patients
