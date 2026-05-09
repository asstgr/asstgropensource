from django.test import TestCase

# Create your tests here.
"""
Full test script for the SaaS public API.

Usage:
    pip install requests
    python test_api.py

Configuration:
    1. Start your Django server: python manage.py runserver
    2. First create an API key via the Django admin or adapt BASE_URL
    3. Fill in the configuration variables below
"""

import requests
import json
import sys
from typing import Optional

# ──────────────────────────────────────────────
# ⚙️  CONFIGURATION — adapt as needed
# ──────────────────────────────────────────────

"""
Full test: configure and call OpenWeatherMap via your SaaS API.

Usage:
    python test_openweather.py

Prerequisites:
    - Your Django server is running: python manage.py runserver
    - Your SaaS API key is configured in API_KEY
    - Your OpenWeatherMap key in OWM_KEY
      (free at https://openweathermap.org/api)
"""

import requests
import json

# ──────────────────────────────────────────────
# ⚙️  CONFIGURATION
# ──────────────────────────────────────────────

BASE_URL = "http://127.0.0.1:8000/api/v1"
API_KEY  = ""       # your SaaS key
OWM_KEY  = ""    # your free OWM key

HEADERS = {
    "Authorization": f"Api-Key {API_KEY}",
    "Content-Type": "application/json",
}

# IDs retrieved as the script progresses
api_id      = None
endpoint_id = None


# ──────────────────────────────────────────────
# 🛠️  Helpers
# ──────────────────────────────────────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def section(title):
    print(f"\n{BOLD}{BLUE}{'─'*55}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'─'*55}{RESET}")

def show(r):
    color = GREEN if r.status_code < 400 else RED
    print(f"  Status : {color}{r.status_code}{RESET}")
    try:
        data = r.json()
        print(f"  Body   :\n{json.dumps(data, indent=4, ensure_ascii=False)[:1200]}")
        return data
    except Exception:
        print(f"  Body   : {r.text[:400]}")
        return {}

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def err(msg):  print(f"  {RED}✗{RESET} {msg}")
def info(msg): print(f"  {YELLOW}→{RESET} {msg}")

def check(r, expected, label):
    if r.status_code == expected:
        ok(f"{label}")
        return True
    err(f"{label} — expected {expected}, got {r.status_code}")
    return False


# ──────────────────────────────────────────────
# STEP 1 — Check available limits
# ──────────────────────────────────────────────

section("STEP 1 — Account limits")

r = requests.get(f"{BASE_URL}/limits/", headers=HEADERS)
data = show(r)
if check(r, 200, "Limits retrieved"):
    usage = data.get("current_usage", {})
    apis_used = usage.get("apis", {}).get("used", "?")
    apis_max  = usage.get("apis", {}).get("max", "?")
    info(f"APIs used: {apis_used}/{apis_max}")


# ──────────────────────────────────────────────
# STEP 2 — Create the OpenWeatherMap API
# ──────────────────────────────────────────────

section("STEP 2 — Create the OpenWeatherMap API")

r = requests.post(f"{BASE_URL}/apis/", headers=HEADERS, json={
    "name":         "OpenWeatherMap",
    "description":  "Current weather data for any location on Earth.",
    "url":          "https://api.openweathermap.org",
    "auth_required": False,   # appid is passed as a query param, not as Bearer
    "is_active":    True,
    "quota_cost":   1,
})
data = show(r)
if check(r, 201, "API created"):
    api_id = data["id"]
    ok(f"api_id = {api_id}")
else:
    # API may already exist — retrieve it from the list
    r2 = requests.get(f"{BASE_URL}/apis/", headers=HEADERS)
    results = r2.json().get("results", [])
    for a in results:
        if "openweather" in a["name"].lower() or "weather" in a["name"].lower():
            api_id = a["id"]
            info(f"Existing API found: id={api_id}")
            break

if not api_id:
    err("Unable to retrieve api_id. Stopping.")
    exit(1)


# ──────────────────────────────────────────────
# STEP 3 — Create the /data/2.5/weather endpoint
# ──────────────────────────────────────────────

section("STEP 3 — Create the /data/2.5/weather endpoint")

r = requests.post(
    f"{BASE_URL}/apis/{api_id}/endpoints/",
    headers=HEADERS,
    json={
        "path":               "/data/2.5/weather",
        "description":        "Current weather for a given lat/lon.",
        "user_input_required": True,
        "example_request":    '{"lat": "48.8566", "lon": "2.3522", "appid": "..."}',
        "example_response":   '{"weather": [...], "main": {"temp": 295.15}}',
    }
)
data = show(r)
if check(r, 201, "Endpoint created"):
    endpoint_id = data["id"]
    ok(f"endpoint_id = {endpoint_id}")
else:
    # Retrieve the existing endpoint
    r2 = requests.get(f"{BASE_URL}/apis/{api_id}/endpoints/", headers=HEADERS)
    results = r2.json().get("results", [])
    if results:
        endpoint_id = results[0]["id"]
        info(f"Existing endpoint found: id={endpoint_id}")

if not endpoint_id:
    err("Unable to retrieve endpoint_id. Stopping.")
    exit(1)


# ──────────────────────────────────────────────
# STEP 4 — Add the GET method
# ──────────────────────────────────────────────

section("STEP 4 — Add the GET method")

r = requests.post(
    f"{BASE_URL}/apis/{api_id}/endpoints/{endpoint_id}/methods/",
    headers=HEADERS,
    json={"method": "GET", "return_code": 200},
)
show(r)
if r.status_code == 201:
    ok("GET method added")
elif r.status_code == 400 and "already exists" in r.text:
    ok("GET method already present")
else:
    err("Problem adding GET method")


# ──────────────────────────────────────────────
# STEP 5 — Add the 3 parameters (lat, lon, appid)
# ──────────────────────────────────────────────

section("STEP 5 — Add parameters lat, lon, appid")

params_to_create = [
    {
        "name":          "lat",
        "param_type":    "query",
        "data_type":     "STRING",
        "required":      True,
        "description":   "Latitude of the location",
        "is_in_url":     False,
        "is_in_body":    False,
        "editable":      True,
        "order":         1,
    },
    {
        "name":          "lon",
        "param_type":    "query",
        "data_type":     "STRING",
        "required":      True,
        "description":   "Longitude of the location",
        "is_in_url":     False,
        "is_in_body":    False,
        "editable":      True,
        "order":         2,
    },
    {
        "name":          "appid",
        "param_type":    "query",
        "data_type":     "STRING",
        "required":      True,
        "description":   "Your OpenWeatherMap API key",
        "stored_value":  OWM_KEY,   # value stored server-side, never exposed
        "is_in_url":     False,
        "is_in_body":    False,
        "editable":      False,     # user cannot modify it
        "order":         3,
    },
]

for p in params_to_create:
    r = requests.post(
        f"{BASE_URL}/apis/{api_id}/endpoints/{endpoint_id}/parameters/",
        headers=HEADERS,
        json=p,
    )
    if r.status_code == 201:
        ok(f"Parameter '{p['name']}' created")
    elif r.status_code == 400 and "already exists" in r.text:
        ok(f"Parameter '{p['name']}' already present")
    else:
        err(f"Problem with '{p['name']}': {r.text[:200]}")


# ──────────────────────────────────────────────
# STEP 6 — Verify the full configuration
# ──────────────────────────────────────────────

section("STEP 6 — Verify the full configuration")

r = requests.get(
    f"{BASE_URL}/apis/{api_id}/endpoints/{endpoint_id}/",
    headers=HEADERS,
)
data = show(r)
if check(r, 200, "Config verified"):
    params   = data.get("parameters", [])
    methods  = data.get("methods", [])
    ok(f"Methods: {[m['method'] for m in methods]}")
    ok(f"Parameters: {[p['name'] for p in params]}")


# ──────────────────────────────────────────────
# STEP 7 — Real call: weather in Paris
# ──────────────────────────────────────────────

section("STEP 7 — Real call: weather in Paris (lat=48.85, lon=2.35)")

r = requests.post(
    f"{BASE_URL}/apis/{api_id}/endpoints/{endpoint_id}/execute/",
    headers=HEADERS,
    json={
        "method": "GET",
        "params": {
            "lat": "48.8566",
            "lon": "2.3522",
            # appid is stored server-side (stored_value), no need to send it
        },
        "display_format": "json",
    },
)
data = show(r)
if check(r, 200, "Weather call successful"):
    result = data.get("result", {})
    quota  = data.get("quota", {})

    # Extract temperature if json format
    if isinstance(result, dict):
        main = result.get("main", {})
        temp_k = main.get("temp")
        if temp_k:
            temp_c = round(temp_k - 273.15, 1)
            ok(f"Temperature in Paris: {temp_c}°C")
        weather = result.get("weather", [{}])[0]
        ok(f"Conditions: {weather.get('description', '?')}")

    ok(f"Remaining quota: {quota.get('remaining')}/{quota.get('limit')}")


# ──────────────────────────────────────────────
# STEP 8 — Call with units=metric
# ──────────────────────────────────────────────

section("STEP 8 — Weather in Roubaix (units=metric)")

# Add the optional units param if it doesn't exist yet
requests.post(
    f"{BASE_URL}/apis/{api_id}/endpoints/{endpoint_id}/parameters/",
    headers=HEADERS,
    json={
        "name": "units", "param_type": "query", "data_type": "STRING",
        "required": False, "description": "Units: standard, metric, imperial",
        "default_value": "metric", "is_in_url": False, "is_in_body": False,
        "editable": True, "order": 4,
    },
)

r = requests.post(
    f"{BASE_URL}/apis/{api_id}/endpoints/{endpoint_id}/execute/",
    headers=HEADERS,
    json={
        "method": "GET",
        "params": {
            "lat":   "50.6942",
            "lon":   "3.1746",
            "units": "metric",
        },
        "display_format": "json",
    },
)
data = show(r)
if check(r, 200, "Roubaix weather OK"):
    result = data.get("result", {})
    if isinstance(result, dict):
        main = result.get("main", {})
        ok(f"Temperature : {main.get('temp')}°C")
        ok(f"Feels like  : {main.get('feels_like')}°C")
        ok(f"Humidity    : {main.get('humidity')}%")

print(f"\n{BOLD}=== Done. api_id={api_id}, endpoint_id={endpoint_id} ==={RESET}")
print(f"{YELLOW}→ Save these IDs for your next calls!{RESET}\n")
"""
# IDs to fill in after running the first read tests
API_ID      = 34 #5   # e.g.: 1
ENDPOINT_ID = 9 #3   # e.g.: 1


# ──────────────────────────────────────────────
# 🛠️  Helpers
# ──────────────────────────────────────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def err(msg):  print(f"  {RED}✗{RESET} {msg}")
def info(msg): print(f"  {YELLOW}→{RESET} {msg}")
def header(title):
    print(f"\n{BOLD}{BLUE}{'─'*50}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'─'*50}{RESET}")

def auth_headers(key: Optional[str] = None) -> dict:
    k = key or API_KEY
    if not k:
        print(f"  {RED}No API key configured.{RESET}")
        sys.exit(1)
    return {
        "Authorization": f"Api-Key {k}",
        "Content-Type": "application/json",
    }

def print_response(r: requests.Response):
    color = GREEN if r.status_code < 400 else RED
    print(f"  Status : {color}{r.status_code}{RESET}")
    try:
        data = r.json()
        print(f"  Body   : {json.dumps(data, indent=4, ensure_ascii=False)[:800]}")
        return data
    except Exception:
        print(f"  Body   : {r.text[:300]}")
        return {}

def assert_status(r, expected, label):
    if r.status_code == expected:
        ok(f"{label} → {r.status_code}")
        return True
    else:
        err(f"{label} → expected {expected}, got {r.status_code}")
        return False


# ──────────────────────────────────────────────
# 🔑  TEST 1: Create an API key
# ──────────────────────────────────────────────

def test_create_key():
    
    # Requires being logged in via Django session OR already having a key.
    # For the first test, use the Django admin to manually create a key,
    # then paste it into API_KEY above.
    
    header("TEST 1 — Create an API key")

    if not API_KEY:
        info("No key configured. Create one via the Django admin:")
        info("  → http://127.0.0.1:8000/admin/api_public/publicapikey/add/")
        info("  → Copy the generated key into the API_KEY variable of this script")
        return None

    r = requests.post(
        f"{BASE_URL}/keys/",
        headers=auth_headers(),
        json={"name": "Test key — Python script"},
    )
    data = print_response(r)
    assert_status(r, 201, "Key creation")

    if r.status_code == 201:
        new_key = data.get("key")
        ok(f"New key: {new_key}")
        info("⚠️  Save this key, it will not be shown again!")
        return new_key

    return None


# ──────────────────────────────────────────────
# 📋  TEST 2: List your keys
# ──────────────────────────────────────────────

def test_list_keys():
    header("TEST 2 — List your API keys")

    r = requests.get(f"{BASE_URL}/keys/", headers=auth_headers())
    data = print_response(r)
    assert_status(r, 200, "List of keys")
    return data


# ──────────────────────────────────────────────
# 📊  TEST 3: Monthly quota
# ──────────────────────────────────────────────

def test_quota():
    header("TEST 3 — Monthly quota")

    r = requests.get(f"{BASE_URL}/quota/", headers=auth_headers())
    data = print_response(r)
    assert_status(r, 200, "Quota")

    if r.status_code == 200:
        used  = data.get("used", "?")
        limit = data.get("limit", "?")
        pct   = data.get("usage_pct", "?")
        ok(f"Used: {used}/{limit} ({pct}%)")

    return data


# ──────────────────────────────────────────────
# 📚  TEST 4: API catalogue
# ──────────────────────────────────────────────

def test_list_apis():
    header("TEST 4 — API catalogue")

    r = requests.get(f"{BASE_URL}/apis/", headers=auth_headers())
    data = print_response(r)
    assert_status(r, 200, "List APIs")

    if r.status_code == 200:
        count = data.get("count", 0)
        ok(f"{count} API(s) available")

        if count > 0:
            first = data["results"][0]
            info(f"First API: [{first['id']}] {first['name']}")
            info(f"  → Copy this ID into the API_ID variable of the script")

    return data


# ──────────────────────────────────────────────
# 🔍  TEST 5: API detail
# ──────────────────────────────────────────────

def test_api_detail():
    header("TEST 5 — API detail")

    if not API_ID:
        info("API_ID not configured — run test_list_apis() first")
        return {}

    r = requests.get(f"{BASE_URL}/apis/{API_ID}/", headers=auth_headers())
    data = print_response(r)
    assert_status(r, 200, f"API detail #{API_ID}")

    if r.status_code == 200:
        endpoints = data.get("endpoints", [])
        ok(f"{len(endpoints)} endpoint(s)")
        for ep in endpoints:
            info(f"  [{ep['id']}] {ep['path']} — methods: {ep['method_list']}")
        if endpoints:
            info(f"→ Copy an endpoint ID into the ENDPOINT_ID variable of the script")

    return data


# ──────────────────────────────────────────────
# 🔎  TEST 6: Endpoint detail
# ──────────────────────────────────────────────

def test_endpoint_detail():
    header("TEST 6 — Endpoint detail")

    if not API_ID or not ENDPOINT_ID:
        info("API_ID or ENDPOINT_ID not configured")
        return {}

    r = requests.get(
        f"{BASE_URL}/apis/{API_ID}/endpoints/{ENDPOINT_ID}/",
        headers=auth_headers(),
    )
    data = print_response(r)
    assert_status(r, 200, f"Endpoint detail #{ENDPOINT_ID}")

    if r.status_code == 200:
        params = data.get("parameters", [])
        ok(f"{len(params)} parameter(s):")
        for p in params:
            required = "required" if p["required"] else "optional"
            info(f"  {p['name']} ({p['param_type']}, {required})")

    return data


# ──────────────────────────────────────────────
# 🚀  TEST 7: Execute an endpoint
# ──────────────────────────────────────────────

def test_execute(params: dict = {}, method: str = "GET", display_format: str = "json"):
    header(f"TEST 7 — Execute endpoint #{ENDPOINT_ID}")

    if not API_ID or not ENDPOINT_ID:
        info("API_ID or ENDPOINT_ID not configured")
        return {}

    payload = {
        "method": method,
        "params": params,
        "display_format": display_format,
    }

    info(f"Payload sent: {json.dumps(payload, indent=2)}")

    r = requests.post(
        f"{BASE_URL}/apis/{API_ID}/endpoints/{ENDPOINT_ID}/execute/",
        headers=auth_headers(),
        json=payload,
    )
    data = print_response(r)
    assert_status(r, 200, "Endpoint execution")

    if r.status_code == 200:
        quota = data.get("quota", {})
        ok(f"Remaining quota: {quota.get('remaining')}/{quota.get('limit')}")

    return data


# ──────────────────────────────────────────────
# 🔒  TEST 8: Expected errors
# ──────────────────────────────────────────────

def test_error_cases():
    header("TEST 8 — Error cases (expected behaviour)")

    # Wrong API key → 403
    r = requests.get(
        f"{BASE_URL}/apis/",
        headers={"Authorization": "Api-Key sk-INVALID123"},
    )
    expected = r.status_code in (401, 403)
    (ok if expected else err)(f"Invalid key → {r.status_code} (expected 401/403)")

    # No auth → 403
    r = requests.get(f"{BASE_URL}/apis/")
    expected = r.status_code in (401, 403)
    (ok if expected else err)(f"No auth → {r.status_code} (expected 401/403)")

    # Non-existent API → 404
    if API_KEY:
        r = requests.get(f"{BASE_URL}/apis/99999/", headers=auth_headers())
        (ok if r.status_code == 404 else err)(f"Non-existent API → {r.status_code} (expected 404)")

    # Invalid method on execute → 400 or 405
    if API_KEY and API_ID and ENDPOINT_ID:
        r = requests.post(
            f"{BASE_URL}/apis/{API_ID}/endpoints/{ENDPOINT_ID}/execute/",
            headers=auth_headers(),
            json={"method": "INVALID", "params": {}},
        )
        (ok if r.status_code == 400 else err)(f"Invalid method → {r.status_code} (expected 400)")


# ──────────────────────────────────────────────
# 🗑️  TEST 9: Revoke a key
# ──────────────────────────────────────────────

def test_revoke_key(key_id: int):
    header(f"TEST 9 — Revoke key #{key_id}")

    r = requests.delete(
        f"{BASE_URL}/keys/{key_id}/",
        headers=auth_headers(),
    )
    print_response(r)
    assert_status(r, 200, "Key revocation")


# ──────────────────────────────────────────────
# ▶️  MAIN RUNNER
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{BOLD}=== Public API test — {BASE_URL} ==={RESET}\n")

    if not API_KEY:
        print(f"{YELLOW}⚠️  No API_KEY configured.{RESET}")
        print("Steps to get started:\n")
        print("  1. Start your server:   python manage.py runserver")
        print("  2. Go to:               http://127.0.0.1:8000/admin/api_public/publicapikey/add/")
        print("  3. Create a key for your user account")
        print("  4. Copy the key into the API_KEY variable of this script")
        print("  5. Re-run:              python test_api.py\n")
        sys.exit(0)

    # ── Step 1: basic info ──
    test_list_keys()
    test_quota()

    # ── Step 2: catalogue ──
    test_list_apis()

    if API_ID:
        test_api_detail()

    if API_ID and ENDPOINT_ID:
        test_endpoint_detail()

        # ── Step 3: execution ──
        # Adapt the params to match your endpoint
        test_execute(
            params={},       # e.g.: {"city": "Paris"} if your endpoint requires it
            method="GET",
            display_format="json",
        )

    # ── Step 4: error cases ──
    test_error_cases()

    print(f"\n{BOLD}=== Tests complete ==={RESET}\n")
"""