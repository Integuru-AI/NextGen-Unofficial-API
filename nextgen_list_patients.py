import re
import base64
import json
from curl_cffi import requests


def run(headers, user_input):
    """List all patients with cursor-based pagination."""
    # Optional filters
    location_id = user_input.get("location_id", "")
    account_status = user_input.get("account_status", "")

    if account_status and account_status.upper() not in ["ACTIVE", "ARCHIVED"]:
        return {'status_code': 400, 'body': {'error': 'account_status must be ACTIVE, ARCHIVED, or omitted'}}

    # Cursor-based pagination
    cursor = user_input.get("cursor")
    limit = user_input.get("limit", 100)

    if not isinstance(limit, int) or limit < 1 or limit > 100:
        return {'status_code': 400, 'body': {'error': 'limit must be between 1 and 100'}}

    # Decode cursor or start from beginning
    if cursor:
        try:
            state = json.loads(base64.b64decode(cursor).decode())
            letter = state.get("l", "a")
            page = state.get("p", 1)
        except:
            return {'status_code': 400, 'body': {'error': 'Invalid cursor'}}
    else:
        letter = "a"
        page = 1

    # Fetch patients until we have enough or run out
    patients = []
    letters = "abcdefghijklmnopqrstuvwxyz"

    while len(patients) < limit and letter in letters:
        try:
            page_patients, has_more = _fetch_patients_page(headers, location_id, letter, page)
        except Exception as e:
            return {'status_code': 500, 'body': {'error': str(e)}}

        if page_patients is None:
            return {'status_code': 401, 'body': {'error': 'Session expired'}}

        # Apply account_status filter if specified
        if account_status:
            page_patients = [p for p in page_patients if p.get('account_status', '').upper() == account_status.upper()]

        patients.extend(page_patients)

        # Move to next page or letter
        if has_more:
            page += 1
        else:
            letter_idx = letters.index(letter)
            if letter_idx < 25:
                letter = letters[letter_idx + 1]
                page = 1
            else:
                letter = None  # Done
                break

    # Trim to limit and create next cursor
    result_patients = patients[:limit]
    has_more_data = len(patients) > limit or (letter is not None and letter in letters)

    next_cursor = None
    if has_more_data and letter:
        next_cursor = base64.b64encode(json.dumps({"l": letter, "p": page}).encode()).decode()

    return {
        'status_code': 200,
        'body': {
            'patients': result_patients,
            'next_cursor': next_cursor
        }
    }


# === PRIVATE ===

def _fetch_patients_page(headers, location_id, letter, page):
    """Fetch a single page of patients for a given letter search."""
    base_url = BASE_URL.rstrip('/')
    url = f"{base_url}/electronic/pm/action.do"

    payload = {
        "ACTION_NAME": "PATIENT_VIEW_DATA",
        "PAGE_NO": str(page),
        "PATIENT_NAME": letter,
        "hdrSearchType": "name",
        "SEARCH_TYPE": "All",
        "LOCATION_ID": location_id,
    }

    response = requests.post(
        url,
        data=payload,
        headers={
            **headers,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Origin": base_url,
            "Referer": f"{base_url}/electronic/pm/pm_dashboard.jsp",
        },
        impersonate="chrome131",
        timeout=30
    )

    # Check for session expiration
    if "userlogin" in response.url or "login" in response.text[:500].lower():
        return None, False

    if response.status_code != 200:
        return [], False

    patients = _parse_patient_table(response.text)
    has_more = "submit_next_page()" in response.text

    return patients, has_more


def _parse_patient_table(html):
    """Parse patient data from HTML table."""
    patients = []

    row_pattern = re.compile(
        r"<tr[^>]*>\s*<TD>.*?PATIENT_CHARGE_ENTRY_ACTION.*?</tr>",
        re.IGNORECASE | re.DOTALL
    )

    member_id_pattern = re.compile(
        r"submit_option\s*\(\s*['\"]PATIENT_CHARGE_ENTRY_ACTION['\"]\s*,\s*['\"](\d+)['\"]",
        re.IGNORECASE
    )

    cell_pattern = re.compile(r"<TD[^>]*>(.*?)</TD>", re.IGNORECASE | re.DOTALL)

    for row_match in row_pattern.finditer(html):
        row_html = row_match.group(0)

        member_match = member_id_pattern.search(row_html)
        if not member_match:
            continue
        member_id = member_match.group(1)

        cells = cell_pattern.findall(row_html)
        if len(cells) < 8:
            continue

        def clean_cell(cell):
            text = re.sub(r'<[^>]+>', '', cell)
            text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
            return text.strip()

        chart_match = re.search(r'class="chartNo"[^>]*>([^<]+)</A>', cells[0], re.IGNORECASE)
        if not chart_match:
            continue
        chart_no = chart_match.group(1).strip()

        status_cell = cells[7] if len(cells) > 7 else ""
        status_match = re.search(r'class=["\']?(active|archived)["\']?', status_cell, re.IGNORECASE)
        if status_match:
            account_status = status_match.group(1).upper()
        else:
            account_status = clean_cell(status_cell)

        patient = {
            'member_id': member_id,
            'chart_no': chart_no,
            'name': clean_cell(cells[1]),
            'dob': clean_cell(cells[2]),
            'phone': clean_cell(cells[4]),
            'primary_insurance': clean_cell(cells[5]),
            'insured_id': clean_cell(cells[6]),
            'account_status': account_status,
        }
        patients.append(patient)

    return patients
