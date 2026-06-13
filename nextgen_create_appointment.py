import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime


def run(headers, user_input):
    """Create a new appointment in NextGen Office (HealthFusion) scheduling system."""

    # Required fields
    member_id = user_input.get("member_id", "")
    appt_type = user_input.get("appt_type", "")
    calendar_resource_id = user_input.get("calendar_resource_id", "")
    location_id = user_input.get("location_id", "")
    current_date = user_input.get("current_date", "")

    if not member_id:
        return {"status_code": 400, "body": {"error": "member_id is required (patient member ID)"}}
    if not appt_type:
        return {"status_code": 400, "body": {"error": "appt_type is required (appointment type ID, e.g. '370301' for ESTABLISHED PATIENT)"}}
    if not calendar_resource_id:
        return {"status_code": 400, "body": {"error": "calendar_resource_id is required (provider/resource ID)"}}
    if not location_id:
        return {"status_code": 400, "body": {"error": "location_id is required"}}
    if not current_date:
        return {"status_code": 400, "body": {"error": "current_date is required (format: 'MM/DD/YYYY H:MM AM/PM', e.g. '02/16/2026 3:45 PM')"}}

    # Optional fields
    notes = user_input.get("notes", "")
    follow_up = user_input.get("follow_up", "")
    transition_of_care = user_input.get("transition_of_care", "1")
    patient_name = user_input.get("patient_name", "")

    try:
        body = _create_appointment(
            headers, member_id, appt_type, calendar_resource_id, location_id,
            current_date, notes, follow_up, transition_of_care, patient_name
        )
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        # Detect session expiry
        if "login" in err_body.lower() and "password" in err_body.lower():
            return {"status_code": 401, "body": {"error": "Session expired"}}
        return {"status_code": e.code, "body": {"error": err_body[:1000]}}

    # Detect session expiry in 200 response
    if "login" in body.lower() and "password" in body.lower():
        return {"status_code": 401, "body": {"error": "Session expired"}}

    # Check for server-side warning messages
    warning_match = re.search(r'id="warningTextNewPage"[^>]*>([^<]+)', body)
    if warning_match:
        warning_text = warning_match.group(1).strip()
        if warning_text:
            return {"status_code": 400, "body": {"error": warning_text}}

    # Success - extract appointment ID if present in response
    appt_id_match = re.search(r'APPOINTMENT_ID["\s]*(?:value=["\']\s*)(\d+)', body)
    appointment_id = appt_id_match.group(1) if appt_id_match else None

    result = {
        "message": "Appointment created successfully",
        "appointment_date": current_date,
        "calendar_resource_id": calendar_resource_id,
        "location_id": location_id,
        "appt_type": appt_type,
        "member_id": member_id,
    }
    if appointment_id:
        result["appointment_id"] = appointment_id

    return {"status_code": 200, "body": result}


# === PRIVATE ===

def _create_appointment(headers, member_id, appt_type, calendar_resource_id, location_id,
                        current_date, notes, follow_up, transition_of_care, patient_name):
    """Submit the appointment creation form to the scheduling API."""
    # Derive dynamic defaults
    now = datetime.now()
    day_of_month = str(now.day)
    checked_date = now.strftime("%m/%d/%Y")

    # Build the complete form data matching all fields from form#appointment
    form_data = {
        # Core action fields
        "ACTION_NAME": "SAVE_APPOINTMENT",
        "APPOINTMENT_ID": "",
        "APPOINTMENT_STATUS": "null",
        "UPDATE_APPOINTMENT_ID": "null",
        "APPOINTMENT_THREAD": "",
        "LOCATION_ID": location_id,
        "CALENDAR_RESOURCE_ID": calendar_resource_id,
        "MEMBER_ID": member_id,
        "NEW_PAGE": "true",
        "MULTI_RESOURCE_IDS": "",
        "CURRENT_DATE": current_date,
        "PRIMARY_POLICY_ID": "",
        "NM_MEMBER_ID": "",
        "RADIO_EDIT": "",
        "CANCEL_NOTE": "",
        "IS_READ_ONLY": "",
        "IS_RECURRENCE": "",
        "COMMENTS": "",
        "ROOM_NUMBER": "",
        "PRIORITY": "null",

        # Recurrence defaults (ignored when IS_RECURRENCE is empty)
        "R_DAYS": "1",
        "R_WEEKNO": "1",
        "R_MONTHDAY": day_of_month,
        "R_NOMONTHONE": "1",
        "R_NOMONTHTWO": "1",
        "R_DAYLISTMO": "2",
        "R_FIRSTLISTMO": "3",
        "R_DATE": day_of_month,
        "R_MONTHLISTONE": "1",
        "R_DAYLISTYR": "2",
        "R_FIRSTLISTYR": "3",
        "R_MONTHLISTTWO": "1",
        "R_CHECKEDDAY": "2",
        "RECURRENCE_APP_ID": "",
        "RECURR_PATTERN": "",

        # Prior authorization defaults (no auth)
        "PRIOR_AUTH": "",
        "AUTHORIZATION_NO": "",
        "AUTHORIZATION_DATE": "",
        "AUTHORIZATION_EXPIRATION_DATE": "",
        "AUTHORIZATION_REF_PROVIDER": "",
        "AUTHORIZATION_PAYER": "",
        "CONTACT_PERSON": "",
        "CONTACT_PHONE": "",
        "AUTHORIZATION_LIMITATION": "null",
        "TIME_RESTRICTION": "",
        "TIME_RESTRICTION_UNIT": "",
        "AUTHORIZATION_POS": "",
        "AUTHORIZATION_NOTES": "",
        "LIMITATION_ICD_CODE": "",
        "LIMITATION_CPT_CODE": "",
        "LIMITATION_CHARGES": "",
        "LIMITATION_VISITS": "",
        "LIMITATION_INSURANCE_PAYMENT": "",
        "LIMITATION_PROVIDER": "",
        "TOTAL_LIMITATIONS": "null",
        "REMAINING_LIMITATIONS": "null",
        "SCHEDULED": "null",

        # Navigation/source flags
        "FROM_SCHEDULE_PAGE": "false",
        "FROM_APPT_SEARCH_PAGE": "false",
        "FROM_TODAYS_PAGE": "false",
        "FROM_PAGE": "",
        "PAGE_NO": "1",
        "FILTER_APPT_TYPE": "",
        "FOLLOW_UP_CHANGE": "true" if follow_up else "false",
        "CHECK_PRIOR_AUTH": "false",

        # Patient/encounter fields
        "ENCOUNTER_ID": "null",
        "PATIENT_NAME_VAL": "",
        "PATIENT_NAME": patient_name,

        # Appointment type and description
        "APPT_TYPE": appt_type,
        "BLOCK_DESC": "",

        # Insurance/eligibility defaults
        "ELIGIBILITY_STATUS": "-1",
        "CHECKED_DATE": checked_date,
        "TRANS_STATUS_ID": "",

        # Condition/episode defaults
        "SELECT_EPISODE": "",
        "EMPLOYMENT_STATUS": "No",
        "ACCIDENT": "No",
        "ACCIDENTstate": "No",
        "ACCIDENT_STATE": "Select",
        "ACCIDENTother": "No",
        "CE_REFERRING_PROVIDER_INTERNAL_ID": "",
        "PRIOR_AUTH_ID": "",

        # Notes and options
        "NOTES": notes.strip() if notes else "",
        "FOLLOW_UP": follow_up,
        "FORM_ID": "",
        "TRANSITION_OF_CARE": transition_of_care,
        "practice_pcmh_flag": "false",
    }

    # URL with cache-busting timestamp
    url = "https://txn2.healthfusionclaims.com/electronic/pm_schedule/action.do?" + str(int(time.time() * 1000))

    post_data = urllib.parse.urlencode(form_data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=post_data,
        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8", errors="replace")
