from django.test import TestCase

# Create your tests here.
"""
Script de test complet pour l'API publique du SaaS.

Usage :
    pip install requests
    python test_api.py

Configuration :
    1. Lance ton serveur Django : python manage.py runserver
    2. Crée d'abord une clé API via l'admin Django ou adapte BASE_URL
    3. Remplis les variables de configuration ci-dessous
"""

import requests
import json
import sys
from typing import Optional

# ──────────────────────────────────────────────
# ⚙️  CONFIGURATION — à adapter
# ──────────────────────────────────────────────

BASE_URL   = "http://127.0.0.1:8000/api/v1"

# Si tu n'as pas encore de clé : laisse vide, le test de création va en générer une
API_KEY    =  "sk-7e8223db3f52437681ebd4de8db1f09108817434"#"sk-a00da7750f1e44718f424e4f22e1348d5b68b727"

"""
Test complet : configurer et appeler OpenWeatherMap via ton SaaS API.

Usage :
    python test_openweather.py

Prérequis :
    - Ton serveur Django tourne : python manage.py runserver
    - Ta clé API SaaS est configurée dans API_KEY
    - Ta clé OpenWeatherMap dans OWM_KEY
      (gratuite sur https://openweathermap.org/api)
"""
"""
import requests
import json

# ──────────────────────────────────────────────
# ⚙️  CONFIGURATION
# ──────────────────────────────────────────────

BASE_URL = "http://127.0.0.1:8000/api/v1"
API_KEY  = "sk-7e8223db3f52437681ebd4de8db1f09108817434"       # ta clé SaaS
OWM_KEY  = "185cb90e6189b77fb636335b7b2d763d"    # ta clé OWM gratuite

HEADERS = {
    "Authorization": f"Api-Key {API_KEY}",
    "Content-Type": "application/json",
}

# IDs récupérés au fur et à mesure du script
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
    err(f"{label} — attendu {expected}, reçu {r.status_code}")
    return False


# ──────────────────────────────────────────────
# ÉTAPE 1 — Vérifier les limites disponibles
# ──────────────────────────────────────────────

section("ÉTAPE 1 — Limites de ton compte")

r = requests.get(f"{BASE_URL}/limits/", headers=HEADERS)
data = show(r)
if check(r, 200, "Limites récupérées"):
    usage = data.get("current_usage", {})
    apis_used = usage.get("apis", {}).get("used", "?")
    apis_max  = usage.get("apis", {}).get("max", "?")
    info(f"APIs utilisées : {apis_used}/{apis_max}")


# ──────────────────────────────────────────────
# ÉTAPE 2 — Créer l'API OpenWeatherMap
# ──────────────────────────────────────────────

section("ÉTAPE 2 — Créer l'API OpenWeatherMap")

r = requests.post(f"{BASE_URL}/apis/", headers=HEADERS, json={
    "name":         "OpenWeatherMap",
    "description":  "Current weather data for any location on Earth.",
    "url":          "https://api.openweathermap.org",
    "auth_required": False,   # l'appid est passé en query param, pas en Bearer
    "visibility":   "private",
    "is_active":    True,
    "quota_cost":   1,
})
data = show(r)
if check(r, 201, "API créée"):
    api_id = data["id"]
    ok(f"api_id = {api_id}")
else:
    # L'API existe peut-être déjà — on la récupère depuis la liste
    r2 = requests.get(f"{BASE_URL}/apis/", headers=HEADERS)
    results = r2.json().get("results", [])
    for a in results:
        if "openweather" in a["name"].lower() or "weather" in a["name"].lower():
            api_id = a["id"]
            info(f"API existante trouvée : id={api_id}")
            break

if not api_id:
    err("Impossible de récupérer l'api_id. Arrêt.")
    exit(1)


# ──────────────────────────────────────────────
# ÉTAPE 3 — Créer l'endpoint /data/2.5/weather
# ──────────────────────────────────────────────

section("ÉTAPE 3 — Créer l'endpoint /data/2.5/weather")

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
if check(r, 201, "Endpoint créé"):
    endpoint_id = data["id"]
    ok(f"endpoint_id = {endpoint_id}")
else:
    # Récupère l'endpoint existant
    r2 = requests.get(f"{BASE_URL}/apis/{api_id}/endpoints/", headers=HEADERS)
    results = r2.json().get("results", [])
    if results:
        endpoint_id = results[0]["id"]
        info(f"Endpoint existant trouvé : id={endpoint_id}")

if not endpoint_id:
    err("Impossible de récupérer l'endpoint_id. Arrêt.")
    exit(1)


# ──────────────────────────────────────────────
# ÉTAPE 4 — Ajouter la méthode GET
# ──────────────────────────────────────────────

section("ÉTAPE 4 — Ajouter la méthode GET")

r = requests.post(
    f"{BASE_URL}/apis/{api_id}/endpoints/{endpoint_id}/methods/",
    headers=HEADERS,
    json={"method": "GET", "return_code": 200},
)
show(r)
if r.status_code == 201:
    ok("Méthode GET ajoutée")
elif r.status_code == 400 and "already exists" in r.text:
    ok("Méthode GET déjà présente")
else:
    err("Problème lors de l'ajout de la méthode GET")


# ──────────────────────────────────────────────
# ÉTAPE 5 — Ajouter les 3 paramètres (lat, lon, appid)
# ──────────────────────────────────────────────

section("ÉTAPE 5 — Ajouter les paramètres lat, lon, appid")

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
        "stored_value":  OWM_KEY,   # valeur stockée côté serveur, jamais exposée
        "is_in_url":     False,
        "is_in_body":    False,
        "editable":      False,     # l'utilisateur ne peut pas la modifier
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
        ok(f"Paramètre '{p['name']}' créé")
    elif r.status_code == 400 and "already exists" in r.text:
        ok(f"Paramètre '{p['name']}' déjà présent")
    else:
        err(f"Problème avec '{p['name']}' : {r.text[:200]}")


# ──────────────────────────────────────────────
# ÉTAPE 6 — Vérifier la configuration complète
# ──────────────────────────────────────────────

section("ÉTAPE 6 — Vérification de la config complète")

r = requests.get(
    f"{BASE_URL}/apis/{api_id}/endpoints/{endpoint_id}/",
    headers=HEADERS,
)
data = show(r)
if check(r, 200, "Config vérifiée"):
    params   = data.get("parameters", [])
    methods  = data.get("methods", [])
    ok(f"Méthodes : {[m['method'] for m in methods]}")
    ok(f"Paramètres : {[p['name'] for p in params]}")


# ──────────────────────────────────────────────
# ÉTAPE 7 — Appel réel : météo de Paris
# ──────────────────────────────────────────────

section("ÉTAPE 7 — Appel réel : météo de Paris (lat=48.85, lon=2.35)")

r = requests.post(
    f"{BASE_URL}/apis/{api_id}/endpoints/{endpoint_id}/execute/",
    headers=HEADERS,
    json={
        "method": "GET",
        "params": {
            "lat": "48.8566",
            "lon": "2.3522",
            # appid est stocké côté serveur (stored_value), pas besoin de l'envoyer
        },
        "display_format": "json",
    },
)
data = show(r)
if check(r, 200, "Appel météo réussi"):
    result = data.get("result", {})
    quota  = data.get("quota", {})

    # Extraire la température si format json
    if isinstance(result, dict):
        main = result.get("main", {})
        temp_k = main.get("temp")
        if temp_k:
            temp_c = round(temp_k - 273.15, 1)
            ok(f"Température à Paris : {temp_c}°C")
        weather = result.get("weather", [{}])[0]
        ok(f"Conditions : {weather.get('description', '?')}")

    ok(f"Quota restant : {quota.get('remaining')}/{quota.get('limit')}")


# ──────────────────────────────────────────────
# ÉTAPE 8 — Appel avec units=metric
# ──────────────────────────────────────────────

section("ÉTAPE 8 — Météo de Roubaix (units=metric)")

# Ajouter le param units optionnel s'il n'existe pas encore
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
if check(r, 200, "Météo Roubaix OK"):
    result = data.get("result", {})
    if isinstance(result, dict):
        main = result.get("main", {})
        ok(f"Température : {main.get('temp')}°C")
        ok(f"Ressenti    : {main.get('feels_like')}°C")
        ok(f"Humidité    : {main.get('humidity')}%")

print(f"\n{BOLD}=== Terminé. api_id={api_id}, endpoint_id={endpoint_id} ==={RESET}")
print(f"{YELLOW}→ Sauvegarde ces IDs pour tes prochains appels !{RESET}\n")
"""
# IDs à remplir après avoir lancé les premiers tests de lecture
API_ID      = 34 #5   # ex: 1
ENDPOINT_ID = 9 #3   # ex: 1


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
        print(f"  {RED}Pas de clé API configurée.{RESET}")
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
        err(f"{label} → attendu {expected}, reçu {r.status_code}")
        return False


# ──────────────────────────────────────────────
# 🔑  TEST 1 : Création d'une clé API
# ──────────────────────────────────────────────

def test_create_key():
    
    #Nécessite d'être connecté via session Django OU d'avoir déjà une clé.
    #Pour le premier test, utilise l'admin Django pour créer une clé manuellement,
    #puis colle-la dans API_KEY ci-dessus.
    
    header("TEST 1 — Créer une clé API")

    if not API_KEY:
        info("Aucune clé configurée. Crée-en une via l'admin Django :")
        info("  → http://127.0.0.1:8000/admin/api_public/publicapikey/add/")
        info("  → Copie la clé générée dans la variable API_KEY de ce script")
        return None

    r = requests.post(
        f"{BASE_URL}/keys/",
        headers=auth_headers(),
        json={"name": "Test key — script Python"},
    )
    data = print_response(r)
    assert_status(r, 201, "Création clé")

    if r.status_code == 201:
        new_key = data.get("key")
        ok(f"Nouvelle clé : {new_key}")
        info("⚠️  Sauvegarde cette clé, elle ne sera plus affichée !")
        return new_key

    return None


# ──────────────────────────────────────────────
# 📋  TEST 2 : Lister ses clés
# ──────────────────────────────────────────────

def test_list_keys():
    header("TEST 2 — Lister ses clés API")

    r = requests.get(f"{BASE_URL}/keys/", headers=auth_headers())
    data = print_response(r)
    assert_status(r, 200, "Liste des clés")
    return data


# ──────────────────────────────────────────────
# 📊  TEST 3 : Quota mensuel
# ──────────────────────────────────────────────

def test_quota():
    header("TEST 3 — Quota mensuel")

    r = requests.get(f"{BASE_URL}/quota/", headers=auth_headers())
    data = print_response(r)
    assert_status(r, 200, "Quota")

    if r.status_code == 200:
        used  = data.get("used", "?")
        limit = data.get("limit", "?")
        pct   = data.get("usage_pct", "?")
        ok(f"Utilisé : {used}/{limit} ({pct}%)")

    return data


# ──────────────────────────────────────────────
# 📚  TEST 4 : Catalogue d'APIs
# ──────────────────────────────────────────────

def test_list_apis():
    header("TEST 4 — Catalogue d'APIs")

    r = requests.get(f"{BASE_URL}/apis/", headers=auth_headers())
    data = print_response(r)
    assert_status(r, 200, "Liste APIs")

    if r.status_code == 200:
        count = data.get("count", 0)
        ok(f"{count} API(s) disponible(s)")

        if count > 0:
            first = data["results"][0]
            info(f"Première API : [{first['id']}] {first['name']}")
            info(f"  → Copie cet ID dans la variable API_ID du script")

    return data


# ──────────────────────────────────────────────
# 🔍  TEST 5 : Détail d'une API
# ──────────────────────────────────────────────

def test_api_detail():
    header("TEST 5 — Détail d'une API")

    if not API_ID:
        info("API_ID non configuré — lance d'abord test_list_apis()")
        return {}

    r = requests.get(f"{BASE_URL}/apis/{API_ID}/", headers=auth_headers())
    data = print_response(r)
    assert_status(r, 200, f"Détail API #{API_ID}")

    if r.status_code == 200:
        endpoints = data.get("endpoints", [])
        ok(f"{len(endpoints)} endpoint(s)")
        for ep in endpoints:
            info(f"  [{ep['id']}] {ep['path']} — méthodes : {ep['method_list']}")
        if endpoints:
            info(f"→ Copie un endpoint ID dans la variable ENDPOINT_ID du script")

    return data


# ──────────────────────────────────────────────
# 🔎  TEST 6 : Détail d'un endpoint
# ──────────────────────────────────────────────

def test_endpoint_detail():
    header("TEST 6 — Détail d'un endpoint")

    if not API_ID or not ENDPOINT_ID:
        info("API_ID ou ENDPOINT_ID non configurés")
        return {}

    r = requests.get(
        f"{BASE_URL}/apis/{API_ID}/endpoints/{ENDPOINT_ID}/",
        headers=auth_headers(),
    )
    data = print_response(r)
    assert_status(r, 200, f"Détail endpoint #{ENDPOINT_ID}")

    if r.status_code == 200:
        params = data.get("parameters", [])
        ok(f"{len(params)} paramètre(s) :")
        for p in params:
            required = "requis" if p["required"] else "optionnel"
            info(f"  {p['name']} ({p['param_type']}, {required})")

    return data


# ──────────────────────────────────────────────
# 🚀  TEST 7 : Exécuter un endpoint
# ──────────────────────────────────────────────

def test_execute(params: dict = {}, method: str = "GET", display_format: str = "json"):
    header(f"TEST 7 — Exécuter l'endpoint #{ENDPOINT_ID}")

    if not API_ID or not ENDPOINT_ID:
        info("API_ID ou ENDPOINT_ID non configurés")
        return {}

    payload = {
        "method": method,
        "params": params,
        "display_format": display_format,
    }

    info(f"Payload envoyé : {json.dumps(payload, indent=2)}")

    r = requests.post(
        f"{BASE_URL}/apis/{API_ID}/endpoints/{ENDPOINT_ID}/execute/",
        headers=auth_headers(),
        json=payload,
    )
    data = print_response(r)
    assert_status(r, 200, "Exécution endpoint")

    if r.status_code == 200:
        quota = data.get("quota", {})
        ok(f"Quota restant : {quota.get('remaining')}/{quota.get('limit')}")

    return data


# ──────────────────────────────────────────────
# 🔒  TEST 8 : Erreurs attendues
# ──────────────────────────────────────────────

def test_error_cases():
    header("TEST 8 — Cas d'erreur (comportement attendu)")

    # Mauvaise clé API → 403
    r = requests.get(
        f"{BASE_URL}/apis/",
        headers={"Authorization": "Api-Key sk-INVALID123"},
    )
    expected = r.status_code in (401, 403)
    (ok if expected else err)(f"Clé invalide → {r.status_code} (attendu 401/403)")

    # Sans auth → 403
    r = requests.get(f"{BASE_URL}/apis/")
    expected = r.status_code in (401, 403)
    (ok if expected else err)(f"Sans auth → {r.status_code} (attendu 401/403)")

    # API inexistante → 404
    if API_KEY:
        r = requests.get(f"{BASE_URL}/apis/99999/", headers=auth_headers())
        (ok if r.status_code == 404 else err)(f"API inexistante → {r.status_code} (attendu 404)")

    # Méthode invalide sur execute → 400 ou 405
    if API_KEY and API_ID and ENDPOINT_ID:
        r = requests.post(
            f"{BASE_URL}/apis/{API_ID}/endpoints/{ENDPOINT_ID}/execute/",
            headers=auth_headers(),
            json={"method": "INVALID", "params": {}},
        )
        (ok if r.status_code == 400 else err)(f"Méthode invalide → {r.status_code} (attendu 400)")


# ──────────────────────────────────────────────
# 🗑️  TEST 9 : Révoquer une clé
# ──────────────────────────────────────────────

def test_revoke_key(key_id: int):
    header(f"TEST 9 — Révoquer la clé #{key_id}")

    r = requests.delete(
        f"{BASE_URL}/keys/{key_id}/",
        headers=auth_headers(),
    )
    print_response(r)
    assert_status(r, 200, "Révocation clé")


# ──────────────────────────────────────────────
# ▶️  RUNNER PRINCIPAL
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{BOLD}=== Test de l'API publique — {BASE_URL} ==={RESET}\n")

    if not API_KEY:
        print(f"{YELLOW}⚠️  Aucune API_KEY configurée.{RESET}")
        print("Étapes pour démarrer :\n")
        print("  1. Lance ton serveur :  python manage.py runserver")
        print("  2. Va sur :             http://127.0.0.1:8000/admin/api_public/publicapikey/add/")
        print("  3. Crée une clé pour ton compte utilisateur")
        print("  4. Copie la clé dans la variable API_KEY de ce script")
        print("  5. Relance :            python test_api.py\n")
        sys.exit(0)

    # ── Étape 1 : infos de base ──
    test_list_keys()
    test_quota()

    # ── Étape 2 : catalogue ──
    test_list_apis()

    if API_ID:
        test_api_detail()

    if API_ID and ENDPOINT_ID:
        test_endpoint_detail()

        # ── Étape 3 : exécution ──
        # Adapte les params selon ton endpoint
        test_execute(
            params={},       # ex: {"city": "Paris"} si ton endpoint le demande
            method="GET",
            display_format="json",
        )

    # ── Étape 4 : cas d'erreur ──
    test_error_cases()

    print(f"\n{BOLD}=== Tests terminés ==={RESET}\n")

