from curl_cffi import requests
from urllib.parse import urlencode
import re


def run(headers, user_input):
    """Create a new patient in the practice management system."""

    # Required fields
    first_name = user_input.get("first_name")
    last_name = user_input.get("last_name")
    gender = user_input.get("gender")
    address1 = user_input.get("address1")
    city = user_input.get("city")
    state = user_input.get("state")
    zip_code = user_input.get("zip")
    home_phone = user_input.get("home_phone")

    # Validate required fields
    if not first_name:
        return {"status_code": 400, "body": {"error": "first_name is required"}}
    if not last_name:
        return {"status_code": 400, "body": {"error": "last_name is required"}}
    if not gender:
        return {"status_code": 400, "body": {"error": "gender is required (Female, Male, or Undifferentiated)"}}
    if not address1:
        return {"status_code": 400, "body": {"error": "address1 is required"}}
    if not city:
        return {"status_code": 400, "body": {"error": "city is required"}}
    if not state:
        return {"status_code": 400, "body": {"error": "state is required (2-letter code)"}}
    if not zip_code:
        return {"status_code": 400, "body": {"error": "zip is required (5 or 9 digits)"}}
    if not home_phone:
        return {"status_code": 400, "body": {"error": "home_phone is required (10 digits)"}}

    # Validate gender value
    valid_genders = ["Female", "Male", "Undifferentiated"]
    if gender not in valid_genders:
        return {"status_code": 400, "body": {"error": f"gender must be one of: {', '.join(valid_genders)}"}}

    # Clean phone number (remove formatting)
    home_phone_clean = "".join(c for c in home_phone if c.isdigit())
    if len(home_phone_clean) != 10:
        return {"status_code": 400, "body": {"error": "home_phone must be exactly 10 digits"}}

    # Clean zip (remove dashes)
    zip_clean = zip_code.replace("-", "")
    if len(zip_clean) not in [5, 9] or not zip_clean.isdigit():
        return {"status_code": 400, "body": {"error": "zip must be 5 or 9 digits"}}

    # Optional fields
    middle_name = user_input.get("middle_name", "")
    suffix = user_input.get("suffix", "")
    date_of_birth = user_input.get("date_of_birth", "")
    address2 = user_input.get("address2", "")
    work_phone = user_input.get("work_phone", "")
    cell_phone = user_input.get("cell_phone", "")
    preferred_phone = user_input.get("preferred_phone", "home")
    email = user_input.get("email", "")
    ssn = user_input.get("ssn", "")
    marital_status = user_input.get("marital_status", "")
    employment_status = user_input.get("employment_status", "Other")
    language = user_input.get("language", "EN")

    # Race/ethnicity with defaults
    race = user_input.get("race", "Unknown")
    ethnicity = user_input.get("ethnicity", "Unknown")

    # Emergency contact (optional)
    emergency_first_name = user_input.get("emergency_first_name", "")
    emergency_middle_name = user_input.get("emergency_middle_name", "")
    emergency_last_name = user_input.get("emergency_last_name", "")
    emergency_relationship = user_input.get("emergency_relationship", "")
    emergency_phone = user_input.get("emergency_phone", "")

    # Validate emergency contact conditional requirement
    if emergency_last_name and not emergency_relationship:
        return {"status_code": 400, "body": {"error": "emergency_relationship is required when emergency_last_name is provided"}}

    # Convert date format from YYYY-MM-DD to MM/DD/YYYY
    dob_formatted = ""
    if date_of_birth:
        try:
            parts = date_of_birth.split("-")
            if len(parts) == 3:
                dob_formatted = f"{parts[1]}/{parts[2]}/{parts[0]}"
        except Exception:
            return {"status_code": 400, "body": {"error": "date_of_birth must be in YYYY-MM-DD format"}}

    # Clean optional phones
    work_phone_clean = ""
    if work_phone:
        work_phone_clean = "".join(c for c in work_phone if c.isdigit())
        if len(work_phone_clean) != 10:
            return {"status_code": 400, "body": {"error": "work_phone must be exactly 10 digits"}}

    cell_phone_clean = ""
    if cell_phone:
        cell_phone_clean = "".join(c for c in cell_phone if c.isdigit())
        if len(cell_phone_clean) != 10:
            return {"status_code": 400, "body": {"error": "cell_phone must be exactly 10 digits"}}

    emergency_phone_clean = ""
    if emergency_phone:
        emergency_phone_clean = "".join(c for c in emergency_phone if c.isdigit())
        if len(emergency_phone_clean) != 10:
            return {"status_code": 400, "body": {"error": "emergency_phone must be exactly 10 digits"}}

    # Clean SSN (remove dashes)
    ssn_clean = ""
    if ssn:
        ssn_clean = ssn.replace("-", "")
        if len(ssn_clean) != 9 or not ssn_clean.isdigit():
            return {"status_code": 400, "body": {"error": "ssn must be exactly 9 digits"}}

    # Map preferred phone to code
    preferred_phone_map = {"home": "0", "work": "1", "cell": "2"}
    preferred_phone_code = preferred_phone_map.get(preferred_phone.lower(), "0")

    # Map race to codes
    race_mapping = {
        "White": ("1", "", "White"),
        "Black or African American": ("2", "", "Black or African American"),
        "American Indian or Alaska Native": ("3", "", "American Indian or Alaska Native"),
        "Asian": ("4", "", "Asian"),
        "Hispanic or Latino": ("6", "", "Hispanic or Latino"),
        "Native Hawaiian or Other Pacific Islander": ("7", "", "Native Hawaiian or Other Pacific Islander"),
        "Unknown": ("0", "", "Unknown"),
        "Patient Declined": ("8", "", "Patient Declined"),
    }
    race_group_code, race_code, race_name = race_mapping.get(race, ("0", "", "Unknown"))

    # Map ethnicity to codes
    ethnicity_mapping = {
        "Hispanic or Latino": ("1", "", "Hispanic or Latino"),
        "Not Hispanic or Latino": ("2", "", "Not Hispanic or Latino"),
        "Unknown": ("0", "", "Unknown"),
        "Patient Declined": ("3", "", "Patient Declined"),
    }
    ethnicity_group_code, ethnicity_code, ethnicity_name = ethnicity_mapping.get(ethnicity, ("0", "", "Unknown"))

    # Build the patient data payload
    patient_data = {
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "suffix": suffix,
        "dob_formatted": dob_formatted,
        "gender": gender,
        "race_group_code": race_group_code,
        "race_code": race_code,
        "race_name": race_name,
        "ethnicity_group_code": ethnicity_group_code,
        "ethnicity_code": ethnicity_code,
        "ethnicity_name": ethnicity_name,
        "language": language,
        "ssn_clean": ssn_clean,
        "address1": address1,
        "address2": address2,
        "city": city,
        "state": state,
        "zip_clean": zip_clean,
        "home_phone_clean": home_phone_clean,
        "work_phone_clean": work_phone_clean,
        "cell_phone_clean": cell_phone_clean,
        "preferred_phone_code": preferred_phone_code,
        "email": email,
        "marital_status": marital_status,
        "employment_status": employment_status,
        "emergency_first_name": emergency_first_name,
        "emergency_middle_name": emergency_middle_name,
        "emergency_last_name": emergency_last_name,
        "emergency_relationship": emergency_relationship,
        "emergency_phone_clean": emergency_phone_clean,
    }

    try:
        # Warm up the session, then submit the patient creation form
        warmup_result = _warmup_session(headers)
        if warmup_result is not None:
            return warmup_result

        response_status, response_url, response_text = _submit_patient(headers, patient_data)
    except Exception as e:
        return {"status_code": 500, "body": {"error": str(e)}}

    # Check for session expiry (redirects to login page)
    if "userlogin.jsp" in response_url or "login.healthfusion.com" in response_url:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if "login" in response_url.lower() or "Sign In" in response_text[:2000]:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    # Check for MFA verification page
    if ('action="/electronic/mfa/' in response_text or
        'id="mfaVerificationForm"' in response_text or
        'Enter the code we sent' in response_text):
        return {"status_code": 401, "body": {"error": "MFA verification required - session expired"}}

    # Parse response for success or error
    if response_status == 200:
        # Check for specific error messages first
        error_text_match = re.search(r'class="errorText"[^>]*>([^<]+)</span>', response_text)
        error_msg_match = re.search(r'<div[^>]*id="errorMessage"[^>]*>([^<]+)</div>', response_text)

        if error_text_match:
            return {"status_code": 400, "body": {"success": False, "error": error_text_match.group(1).strip()}}

        if error_msg_match:
            return {"status_code": 400, "body": {"success": False, "error": error_msg_match.group(1).strip()}}

        # Look for MEMBER_ID in response
        member_id_match = re.search(r'MEMBER_ID["\s:=]+["\']?(\d+)', response_text)
        if member_id_match:
            return {"status_code": 200, "body": {"success": True, "patient_id": member_id_match.group(1), "message": "Patient created successfully"}}

        # Check for patObjId in URL or response body
        if "patObjId=" in response_url:
            match = re.search(r'patObjId=(\d+)', response_url)
            if match:
                return {"status_code": 200, "body": {"success": True, "patient_id": match.group(1), "message": "Patient created successfully"}}

        pat_match = re.search(r'patObjId["\']?\s*[:=]\s*["\']?(\d+)', response_text)
        if pat_match:
            return {"status_code": 200, "body": {"success": True, "patient_id": pat_match.group(1), "message": "Patient created successfully"}}

        # If patient name appears in the response, it was likely created
        if first_name in response_text and last_name in response_text:
            return {"status_code": 200, "body": {"success": True, "message": "Patient created successfully (ID not extracted)"}}

        return {"status_code": 200, "body": {"success": True, "message": "Patient creation request submitted"}}

    return {"status_code": response_status, "body": {"success": False, "error": f"Request failed with status {response_status}"}}


# === PRIVATE ===

BASE_URL = "https://txn2.healthfusionclaims.com/"


def _warmup_session(headers):
    """Warm up session by visiting the patient information page."""
    warmup_headers = {
        **headers,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Upgrade-Insecure-Requests": "1",
    }

    warmup_response = requests.get(
        f"{BASE_URL}electronic/pm/patient_information.jsp",
        headers=warmup_headers,
        impersonate="chrome131",
        timeout=30,
        allow_redirects=True,
    )

    # Check if warmup redirected to login
    if "userlogin.jsp" in warmup_response.url or "login" in warmup_response.url.lower():
        return {"status_code": 401, "body": {"error": "Session expired"}}

    # Check for actual MFA verification page
    if ('action="/electronic/mfa/' in warmup_response.text or
        'id="mfaVerificationForm"' in warmup_response.text or
        'Enter the code we sent' in warmup_response.text):
        return {"status_code": 401, "body": {"error": "MFA verification required - session expired"}}

    return None


def _submit_patient(headers, patient_data):
    """Submit the patient creation form and return (status_code, url, text)."""
    # Build form data payload matching the expected request structure
    payload = {
        "patObjId": "",
        "ACTION_NAME": "PATIENT_SAVE",
        "MEMBER_ID": "",
        "EMPLOYER_ID": "",
        "LOCATION_ID": "",
        "LOCATION_NAME": "",
        "REF_ID": "",
        "SSN": patient_data["ssn_clean"],
        "EMPLOYER_PHONE": "",
        "HOME_PHONE": patient_data["home_phone_clean"],
        "WORK_PHONE": patient_data["work_phone_clean"],
        "CELL_PHONE": patient_data["cell_phone_clean"],
        "PREFERRED_PHONE": patient_data["preferred_phone_code"],
        "EMERGENCY_PHONE": patient_data["emergency_phone_clean"],
        "PRIMARY_CAREGIVER_PHONE": "",
        "HEALTH_PROXY_PHONE": "",
        "LEGAL_GUARDIAN_PHONE": "",
        "SEARCH_TYPE": "Patient",
        "INSURANCE_EDI_ERROR_MESSAGE": "",
        "POLICY_INFO_ID": "null",
        "HAS_PRIMARY_INSURANCE": "false",
        "APPOINTMENT_ID": "",
        "NM_MEMBER_ID": "",
        "backbutton": "2",
        "patient_token": "null",
        "PATIENT_SAFE_SAVE": "",
        "TRANSRESLISTID": "",
        "dependentid": "null",
        "locationSearch": "",
        "FIRST_NAME": patient_data["first_name"],
        "MIDDLE_NAME": patient_data["middle_name"],
        "LAST_NAME": patient_data["last_name"],
        "SUFFIX": patient_data["suffix"],
        "PREV_FIRST_NAME": "",
        "PREV_LAST_NAME": "",
        "DOB": patient_data["dob_formatted"],
        "GENDER": patient_data["gender"],
        "SEXUAL_ORIENTATION": "",
        "SEXUAL_ORIENTATION_OTHER": "",
        "GENDER_IDENTITY": "",
        "GENDER_IDENTITY_OTHER": "",
        "RACE_GROUP_CODE_0": patient_data["race_group_code"],
        "RACE_CODE_0": patient_data["race_code"],
        "RACE_NAME_0": patient_data["race_name"],
        "RACE_ID_0": "",
        "ETHNICITY_GROUP_CODE_0": patient_data["ethnicity_group_code"],
        "ETHNICITY_CODE_0": patient_data["ethnicity_code"],
        "ETHNICITY_NAME_0": patient_data["ethnicity_name"],
        "ETHNICITY_ID_0": "",
        "LANGUAGE": patient_data["language"],
        "COUNTRY": "US",
        "SSN1": "",
        "SSN2": "",
        "SSN3": "",
        "ADDRESS1": patient_data["address1"],
        "ADDRESS2": patient_data["address2"],
        "ADDRESS3": "",
        "CITY": patient_data["city"],
        "STATE": patient_data["state"],
        "ZIP": patient_data["zip_clean"],
        "MARITAL_STATUS": patient_data["marital_status"],
        "EMPLOYMENT_STATUS": patient_data["employment_status"],
        "EMPLOYER_NAME": "",
        "emrAreacode": "",
        "emrPrefix": "",
        "emrNumber": "",
        "INT_EMPLOYER_PHONE": "",
        "EMPLOYER_ADDRESS_1": "",
        "EMPLOYER_ADDRESS_2": "",
        "EMPLOYER_ADDRESS_3": "",
        "EMPLOYER_CITY": "",
        "EMPLOYER_STATE": "",
        "EMPLOYER_ZIP": "",
        "OCCUPATION": "",
        "OCCUPATION_CONCEPT_CODE": "",
        "isDropdownSelected": "false",
        "OCCUPATION_INDUSTRY": "",
        "OCCUPATION_INDUSTRY_CONCEPT_CODE": "",
        "isDropdownIndustrySelected": "false",
        "OCCUPATION_START_DATE": "",
        "MULTIPLE_BIRTH_INDICATOR": "NO",
        "MOTHER_MAIDEN_NAME": "",
        "MEMBER_PREVIOUS_ADDRESS_ID": "",
        "PREVIOUS_ADDRESS_ADDRESS1": "",
        "PREVIOUS_ADDRESS_ADDRESS2": "",
        "PREVIOUS_ADDRESS_CITY": "",
        "PREVIOUS_ADDRESS_STATE": "",
        "PREVIOUS_ADDRESS_ZIP": "",
        "PATIENT_ACCOUNT_NO": "",
        "STR_EXTERNAL_MEMBER_ID": "",
        "DATE_REGISTERED": "",
        "CHART_TYPE": "",
        "CUSTOM_CHART_TYPE_ABV": "",
        "CUSTOM_CHART_TYPE_DESC": "",
        "DATE_INJURED": "",
        "ACCOUNT_STATUS": "CURRENT",
        "SECONDARY_STATUS": "",
        "DOD": "",
        "SIGNATURE_ON_FILE": "true",
        "Home Phone area code": "",
        "Home Phone number": "",
        "preferredPhone": patient_data["preferred_phone_code"],
        "INT_HOME_PHONE": "",
        "preferredPhoneInt": "0",
        "Work Phone area code": "",
        "Work Phone number": "",
        "INT_WORK_PHONE": "",
        "EXTENSION": "",
        "pCellAreacode": "",
        "pCellPrefix": "",
        "pCellNumber": "",
        "INT_CELL_PHONE": "",
        "EMAIL": patient_data["email"],
        "RECEIVE_EMAIL": "true",
        "RECEIVE_SMS": "true",
        "CONTACT_PREFERENCE": "Mail",
        "EMERGENCY_FIRST_NAME": patient_data["emergency_first_name"],
        "EMERGENCY_MIDDLE_NAME": patient_data["emergency_middle_name"],
        "EMERGENCY_LAST_NAME": patient_data["emergency_last_name"],
        "INT_EMERGENCY_PHONE": "",
        "EMERGENCY_RELATIONSHIP": patient_data["emergency_relationship"],
        "EMERGENCY_ADDRESS1": "",
        "EMERGENCY_ADDRESS2": "",
        "EMERGENCY_ADDRESS3": "",
        "EMERGENCY_CITY": "",
        "EMERGENCY_STATE": "",
        "EMERGENCY_ZIP": "",
        "PRIMARY_CAREGIVER_ID": "",
        "PRIMARY_CAREGIVER_FIRSTNAME": "",
        "PRIMARY_CAREGIVER_MIDDLENAME": "",
        "PRIMARY_CAREGIVER_LASTNAME": "",
        "PRIMARY_CAREGIVER_RELATIONSHIP": "",
        "pcgAreacode": "",
        "pcgPrefix": "",
        "pcgNumber": "",
        "INT_PRIMARY_CAREGIVER_PHONE": "",
        "PRIMARY_CAREGIVER_ADDRESS1": "",
        "PRIMARY_CAREGIVER_ADDRESS2": "",
        "PRIMARY_CAREGIVER_CITY": "",
        "PRIMARY_CAREGIVER_STATE": "",
        "PRIMARY_CAREGIVER_ZIP": "",
        "PRIMARY_CAREGIVER_COMMENTS": "",
        "LEGAL_GUARDIAN_ID": "",
        "LEGAL_GUARDIAN_FIRSTNAME": "",
        "LEGAL_GUARDIAN_MIDDLENAME": "",
        "LEGAL_GUARDIAN_LASTNAME": "",
        "LEGAL_GUARDIAN_RELATIONSHIP": "",
        "lgAreacode": "",
        "lgPrefix": "",
        "lgNumber": "",
        "INT_LEGAL_GUARDIAN_PHONE": "",
        "LEGAL_GUARDIAN_ADDRESS1": "",
        "LEGAL_GUARDIAN_ADDRESS2": "",
        "LEGAL_GUARDIAN_CITY": "",
        "LEGAL_GUARDIAN_STATE": "",
        "LEGAL_GUARDIAN_ZIP": "",
        "LEGAL_GUARDIAN_COMMENTS": "",
        "HEALTH_PROXY_ID": "",
        "HEALTH_PROXY_FIRSTNAME": "",
        "HEALTHCARE_PROXY_MIDDLENAME": "",
        "HEALTH_PROXY_LASTNAME": "",
        "HEALTH_PROXY_RELATIONSHIP": "",
        "INT_HEALTH_PROXY_PHONE": "",
        "HEALTHCARE_PROXY_ADDRESS1": "",
        "HEALTHCARE_PROXY_ADDRESS2": "",
        "HEALTHCARE_PROXY_CITY": "",
        "HEALTHCARE_PROXY_STATE": "",
        "HEALTHCARE_PROXY_ZIP": "",
        "HEALTH_PROXY_COMMENTS": "",
        "practice_pcmh_flag": "false",
    }

    request_headers = {
        **headers,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Origin": BASE_URL.rstrip("/"),
        "Referer": f"{BASE_URL}electronic/pm/patient_information.jsp",
        "Upgrade-Insecure-Requests": "1",
    }

    response = requests.post(
        f"{BASE_URL}electronic/pm/action.do",
        data=urlencode(payload),
        headers=request_headers,
        impersonate="chrome131",
        timeout=30,
        allow_redirects=True,
    )

    return response.status_code, response.url, response.text
