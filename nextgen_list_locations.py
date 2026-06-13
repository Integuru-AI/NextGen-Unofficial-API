import json
import urllib.request


def run(headers, user_input):
    """List all practice locations and return their location IDs, names, and details.

    No input required. Returns all locations for the authenticated account.
    """
    try:
        data = _call_api(headers)
    except Exception as e:
        error_msg = str(e)
        if "Session expired" in error_msg:
            return {"status_code": 401, "body": {"error": "Session expired"}}
        return {"status_code": 500, "body": {"error": error_msg}}

    # Response is an array; first element contains practiceLocations
    practice_locations = data[0].get("practiceLocations", [])

    # Flatten the state-grouped structure into a single list
    locations = []
    for state_group in practice_locations:
        for loc in state_group.get("Locations", []):
            locations.append({
                "locationID": loc.get("locationID"),
                "locationName": loc.get("locationName"),
                "address": loc.get("address1", ""),
                "city": loc.get("locationCity", ""),
                "state": loc.get("state", ""),
                "zip": loc.get("zip", ""),
                "phone": loc.get("locationPhone", ""),
                "myLocation": loc.get("myLocation", False),
                "isERX": loc.get("isERX", False),
            })

    return {"status_code": 200, "body": {"locations": locations}}


# === PRIVATE ===

def _call_api(headers):
    """Fetch locations from the API."""
    url = "https://txn2.healthfusionclaims.com/electronic/ehr/action.do?ACTION_NAME=GET_MY_LOCATION"

    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 401 or e.code == 403:
            raise Exception("Session expired")
        raise Exception(f"HTTP {e.code}: {str(e)}")

    # Check for login page redirect (session expired returns 200 with HTML)
    if raw.strip().startswith("<!") or raw.strip().startswith("<html") or raw.strip().startswith("<HTML"):
        raise Exception("Session expired")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise Exception("Session expired - invalid JSON response")
