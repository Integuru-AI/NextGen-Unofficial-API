import re
import html as html_module
from curl_cffi import requests


def run(headers, user_input):
    """Query appointments for a location and date, including patient phone numbers."""

    # Validate required inputs
    location_id = user_input.get("location_id")
    date = user_input.get("date")  # Expected: MM/DD/YYYY

    if not location_id:
        return {"status_code": 400, "body": {"error": "location_id is required"}}
    if not date:
        return {"status_code": 400, "body": {"error": "date is required"}}

    # Fetch appointments page
    try:
        page_html = _fetch_appointments_page(headers, location_id, date)
    except PermissionError:
        return {"status_code": 401, "body": {"error": "Session expired"}}
    except Exception as e:
        return {"status_code": 500, "body": {"error": f"Failed to fetch appointments: {str(e)}"}}

    # Find the appointments table
    table_match = re.search(r'id="dailySchedAppts"(.*?)</TABLE>', page_html, re.DOTALL | re.IGNORECASE)
    if not table_match:
        return {"status_code": 200, "body": {
            "date": date,
            "location_id": location_id,
            "count": 0,
            "appointments": []
        }}

    table_html = table_match.group(1)

    # Parse appointment rows
    all_appointments, patient_ids = _parse_appointment_rows(table_html)

    # Fetch phone numbers from patient demographics
    patient_phones = _fetch_patient_phones(headers, patient_ids)

    for appt in all_appointments:
        appt["phone"] = patient_phones.get(appt["patient_id"], "")

    return {
        "status_code": 200,
        "body": {
            "date": date,
            "location_id": location_id,
            "count": len(all_appointments),
            "appointments": all_appointments
        }
    }


# === PRIVATE ===


BASE_URL = "https://txn2.healthfusionclaims.com"


def _fetch_appointments_page(headers, location_id, date):
    """Fetch the Today's Appointments HTML page."""
    resp = requests.post(
        f"{BASE_URL}/electronic/pm/action.do",
        data={
            "ACTION_NAME": "TODAYS_APPOINTMENTS_DISPLAY",
            "FILTER_DATE": date,
            "FILTER_LOCATION": location_id,
            "FILTER_RESOURCE": "",
            "ALL_RESOURCES": "true",
            "PAGE_NO": "0",
            "DAY_MOVE_INCREMENT": "0"
        },
        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        impersonate="chrome131",
        timeout=30
    )

    if "userlogin.jsp" in resp.text.lower():
        raise PermissionError("Session expired")

    if resp.status_code != 200:
        raise Exception(f"HTTP {resp.status_code}")

    return resp.text


def _parse_appointment_rows(table_html):
    """Parse appointment data from the schedule table HTML."""
    # Pattern to extract data from show_current_appt_menu JS calls within each row
    # Params: (event, apptid, resid, locid, encounterId, checkelig, status, newpatientid, patientid, claimid)
    menu_pattern = re.compile(
        r"show_current_appt_menu\(event,"
        r"\s*'(\d+)'\s*,"    # apptid
        r"\s*'(\d*)'\s*,"    # resid
        r"\s*'(\d*)'\s*,"    # locid
        r"\s*'([^']*)'\s*,"  # encounterId
        r"\s*'([^']*)'\s*,"  # checkelig
        r"\s*'([^']*)'\s*,"  # status
        r"\s*'([^']*)'\s*,"  # newpatientid
        r"\s*'(\d*)'\s*,"    # patientid
        r"\s*'([^']*)'\s*"   # claimid
        r"\)",
        re.DOTALL
    )

    # Extract each appointment row by its id="apt{apptid}" pattern
    row_pattern = re.compile(
        r'<TR[^>]*class="datacell"[^>]*id="apt(\d+)"[^>]*>(.*?)</TR>',
        re.DOTALL | re.IGNORECASE
    )

    all_appointments = []
    patient_ids = set()

    for row_match in row_pattern.finditer(table_html):
        row_html = row_match.group(2)

        # Extract structured data from JS menu call
        menu_match = menu_pattern.search(row_html)
        if not menu_match:
            continue

        appt_id, _, _, encounter_id, _, status, _, patient_id, claim_id = menu_match.groups()
        patient_ids.add(patient_id)

        # Extract table cells
        cells = re.findall(r'<TD[^>]*>(.*?)</TD>', row_html, re.DOTALL | re.IGNORECASE)

        # Cell 0: Time (e.g., "10:00 AM")
        time_text = ""
        if len(cells) > 0:
            time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', cells[0])
            if time_match:
                time_text = time_match.group(1)

        # Cell 2: Chart number
        chart = ""
        if len(cells) > 2:
            chart_text = re.sub(r'<[^>]+>', '', cells[2]).strip()
            if chart_text:
                chart = chart_text

        # Cell 3: Patient name
        patient_name = ""
        if len(cells) > 3:
            name_text = re.sub(r'<[^>]+>', '', cells[3])
            name_text = html_module.unescape(name_text)
            name_text = name_text.replace('\xa0', ' ').strip()
            patient_name = re.sub(r'\s+', ' ', name_text).strip()

        # Cell 4: Appointment type (first div only, exclude notes)
        appt_type = ""
        if len(cells) > 4:
            type_match = re.search(r'<div>(.*?)</div>', cells[4], re.DOTALL)
            if type_match:
                appt_type = re.sub(r'<[^>]+>', '', type_match.group(1)).strip()

        # Cell 5: Provider
        provider = ""
        if len(cells) > 5:
            provider_text = re.sub(r'<[^>]+>', '', cells[5])
            provider_text = html_module.unescape(provider_text)
            provider = provider_text.replace('\xa0', ' ').strip()
            provider = re.sub(r'\s+', ' ', provider).strip()

        all_appointments.append({
            "appointment_id": appt_id,
            "time": time_text,
            "patient_id": patient_id,
            "patient": patient_name,
            "encounter_id": encounter_id,
            "appointment_type": appt_type,
            "status": status,
            "provider": provider,
            "billing_slip": claim_id,
            "chart": chart,
            "phone": ""
        })

    return all_appointments, patient_ids


def _fetch_patient_phones(headers, patient_ids):
    """Fetch phone numbers from patient demographics for a set of patient IDs."""
    patient_phones = {}
    for pid in patient_ids:
        try:
            demo_resp = requests.get(
                f"{BASE_URL}/electronic/ehr/action.do",
                params={
                    "ACTION_NAME": "GET_SLIDE_PANEL_PATIENT_DEMOGRAPHICS",
                    "MEMBER_ID": pid
                },
                headers=headers,
                impersonate="chrome131",
                timeout=15
            )
            if demo_resp.status_code == 200:
                data = demo_resp.json()
                if data and len(data) > 0:
                    patient_phones[pid] = data[0].get("preferredPhone", "")
        except Exception:
            pass

    return patient_phones
