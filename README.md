# Asstgr — Outbound API Gateway

> A self-hosted Django platform to manage, proxy, and rate-limit calls to third-party APIs — with OAuth 2.0 support, per-user quota, and a unified REST interface.

---

## ⭐ Like this project?

If Asstgr saved you time or gave you ideas, a GitHub star goes a long way — it helps other developers discover the project and keeps me motivated to build more.

**[⭐ Star it on GitHub](https://github.com/botyut/asstgr)** — it takes 2 seconds and means a lot. Thank you!

---

## ☁️ Hosted Version Available

**Don't want to self-host?** [**asstgr.com**](https://www.asstgr.com/home/) is the fully managed SaaS version of this project — no setup, no infrastructure.

The SaaS version includes everything in this open-source release, plus a significantly more advanced dashboard:

- **Visual API builder** — create and configure APIs, endpoints, parameters, headers, and methods through a polished UI without touching the API directly
- **Live execution interface** — run endpoint calls directly from the dashboard with a chat-style history, formatted response display, and one-click JSON download
- **OAuth2 flow management** — authorize, refresh tokens, and monitor token status visually per API
- **Real-time quota tracking** — progress bar and usage breakdown updated after every call
- **API key management UI** — generate, name, copy, and revoke `sk-...` keys from the browser
- **Request analytics** — bar chart of calls per API over the last 30 days
- **Audit logs** — per-user call history with status codes and response metadata

> The open-source version gives you the full backend, REST API, and admin panel. The SaaS version wraps it in a production-ready interface built for day-to-day use.

👉 [Try the hosted version at asstgr.com](https://www.asstgr.com/home/) · [Star the open-source repo](https://github.com/botyut/asstgr)

---

## What is Asstgr?

**Asstgr** is an **outbound API gateway**: instead of integrating third-party APIs directly into your apps, you register them once in Asstgr, describe their endpoints and parameters, and call them through a single, secured interface.

Think of it as your own private [RapidAPI](https://rapidapi.com/) — self-hosted, fully programmable via REST, with fine-grained quota control.

```
Your app  ──►  Asstgr (/api/v1/...execute/)  ──►  Stripe / OpenWeatherMap / GitHub / any API
                  │
                  ├─ Auth (API Key or OAuth2)
                  ├─ Quota enforcement
                  ├─ Request logging
                  └─ Response formatting
```

---

## Features

- **API Registry** — Register any third-party API with its base URL, authentication, and endpoints
- **Endpoint modeling** — Describe paths, parameters (query / path / body), HTTP headers, and methods
- **Unified execution** — Call any registered endpoint via `/api/v1/.../execute/` with parameters
- **OAuth 2.0** — Full support for `client_credentials`, `authorization_code`, and `password` flows, with automatic token refresh
- **API Key auth** — Generate and revoke personal API keys (`sk-...`) to authenticate against Asstgr
- **Quota system** — Per-user monthly credit budget; each API can have a configurable `quota_cost`
- **Rate limiting** — Burst (30/s) and sustained (1000/day) throttling per API key
- **Response formatting** — JSON, compact, standard, or verbose (human-readable) output modes
- **Full audit logs** — Every call is logged with user, endpoint, status code, and response size
- **Django Admin** — Complete back-office to manage APIs, quotas, keys, and logs

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Auth | Custom API Key + SimpleJWT + OAuth 2.0 |
| Database | PostgreSQL |
| Async | Daphne / Django Channels (ASGI) |
| Throttling | DRF SimpleRateThrottle |

---

## Project Structure

```
asstgrv7/
├── asstgrv7/               # Django project (settings, urls, asgi)
│   ├── settings/
│   │   └── dev.py
│   └── urls.py
│
├── api_management/         # Core: API registry, models, OAuth service
│   ├── models.py           # API, Endpoint, Parameter, Header, Method, APILog, APICallQuota
│   ├── utils.py            # Request building, response formatting (JSONCleaner)
│   ├── oauth_service.py    # OAuthService: fetch, refresh, save tokens
│   ├── views_oauth.py      # OAuth authorize / callback views
│   └── admin.py
│
├── api_public/             # Public REST API (v1)
│   ├── views.py            # All API views (CRUD + Execute + OAuth)
│   ├── models.py           # PublicAPIKey
│   ├── serializers.py
│   ├── authentication.py   # APIKeyAuthentication
│   ├── permissions.py      # IsAPIKeyAuthenticated, HasSufficientQuota
│   ├── throttling.py       # Burst + Sustained throttles
│   ├── limits.py           # LIMITS constants
│   └── urls.py
│
└── users/                  # Custom user model (AbstractUser)
    ├── models.py
    └── admin.py
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/botyut/asstgr.git
cd asstgr
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file at the project root:

```env
DJANGO_SECRET_KEY=your-secret-key

DB_NAME_local=asstgr_db
DB_USER_local=postgres
DB_PASSWORD_local=your-password
DB_HOST_local=localhost
DB_PORT_local=5432
```

### 3. Run migrations & create superuser

```bash
python manage.py migrate --settings=asstgrv7.settings.dev
python manage.py createsuperuser --settings=asstgrv7.settings.dev
```

### 4. Start the server

```bash
python manage.py runserver --settings=asstgrv7.settings.dev
```

The API is available at `http://localhost:8000/api/v1/`.

---

## API Usage

### Authentication

All requests to `/api/v1/` must include your API key:

```http
Authorization: Api-Key sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

Generate a key from the admin panel or via:

```http
POST /api/v1/keys/
Content-Type: application/json

{ "name": "My production key" }
```

---

### Workflow: Register and call an API

#### Step 1 — Register an API

```http
POST /api/v1/apis/
{
  "name": "OpenWeatherMap",
  "url": "https://api.openweathermap.org/data/2.5",
  "auth_required": true,
  "quota_cost": 1
}
```

#### Step 2 — Add an endpoint

```http
POST /api/v1/apis/{api_id}/endpoints/
{
  "path": "/weather",
  "description": "Current weather by city"
}
```

#### Step 3 — Add parameters

```http
POST /api/v1/apis/{api_id}/endpoints/{endpoint_id}/parameters/
{
  "name": "q",
  "param_type": "query",
  "data_type": "STRING",
  "required": true,
  "description": "City name"
}
```

#### Step 4 — Add HTTP method

```http
POST /api/v1/apis/{api_id}/endpoints/{endpoint_id}/methods/
{ "method": "GET" }
```

#### Step 5 — Execute

```http
POST /api/v1/apis/{api_id}/endpoints/{endpoint_id}/execute/
{
  "method": "GET",
  "params": { "q": "Paris" },
  "display_format": "standard"
}
```

Response:

```json
{
  "status_code": 200,
  "result": "...",
  "quota": {
    "used": 3,
    "remaining": 97,
    "limit": 100,
    "usage_pct": 3.0
  }
}
```

---

## API Reference

### API Keys

| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/keys/` | List your API keys |
| POST | `/api/v1/keys/` | Create a new key |
| DELETE | `/api/v1/keys/{id}/` | Revoke a key |

### Quota & Limits

| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/quota/` | Current usage + remaining quota |
| GET | `/api/v1/limits/` | Platform resource limits |

### APIs

| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/apis/` | List your APIs |
| POST | `/api/v1/apis/` | Create an API |
| GET | `/api/v1/apis/{id}/` | Get API details |
| PATCH | `/api/v1/apis/{id}/` | Update an API |
| DELETE | `/api/v1/apis/{id}/` | Delete an API |

### Endpoints / Parameters / Headers / Methods

All follow the same nested pattern under `/api/v1/apis/{api_id}/endpoints/...` — see the full reference in the developer documentation at `/docs/`.

### Execute

| Method | URL | Description |
|---|---|---|
| POST | `/api/v1/apis/{api_id}/endpoints/{endpoint_id}/execute/` | Call the third-party API |

**Body:**

```json
{
  "method": "GET",
  "params": { "key": "value" },
  "display_format": "json"
}
```

`display_format` options: `json` · `compact` · `standard` · `verbose`

### OAuth 2.0

| Method | URL | Description |
|---|---|---|
| GET / POST / PATCH / DELETE | `/api/v1/apis/{id}/oauth/` | Manage OAuth config |
| GET | `/api/v1/apis/{id}/oauth/token/` | Check token status |
| POST | `/api/v1/apis/{id}/oauth/token/` | Force token refresh |

---

## Quota System

Each user has a monthly credit budget managed by `APICallQuota`. Each API has a configurable `quota_cost` (default: 1).

```
User budget: 100 credits/month
API quota_cost: 5
→ User can make 20 calls to this API per month
```

Superusers can set `monthly_limit = NULL` for unlimited access.

---

## Resource Limits

| Resource | Default limit |
|---|---|
| APIs per account | 100 |
| Endpoints per API | 10 |
| Parameters per endpoint | 15 |
| Headers per endpoint | 10 |
| API keys per account | 5 |

---

## Rate Limiting

Applied per API key via DRF throttling:

| Type | Rate |
|---|---|
| Burst | 30 requests / second |
| Sustained | 1000 requests / day |

Exceeded limits return `429 Too Many Requests`.

---

## Response Formats

The `JSONCleaner` engine transforms raw API responses into readable output:

| Format | Description |
|---|---|
| `json` | Raw pretty-printed JSON |
| `compact` | Flat key:value, no emojis |
| `standard` | Human-readable with smart formatting |
| `verbose` | Fully expanded with all nested objects |

---

## Environment Variables

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DB_NAME_local` | PostgreSQL database name |
| `DB_USER_local` | PostgreSQL user |
| `DB_PASSWORD_local` | PostgreSQL password |
| `DB_HOST_local` | PostgreSQL host |
| `DB_PORT_local` | PostgreSQL port |

---

## License

MIT — feel free to use, modify, and distribute.

---

## Author

Built with Django + DRF. Contributions welcome.

- 🌐 Hosted version: [asstgr.com](https://www.asstgr.com/home/)
- 💻 Open-source: [github.com/botyut/asstgr](https://github.com/botyut/asstgr)
- ⭐ If this project helped you, [leave a star](https://github.com/botyut/asstgr) — it's the best way to support the work!