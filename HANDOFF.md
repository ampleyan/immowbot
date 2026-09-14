# Immowbot — Project Handoff

## What this project is

A private property buyer assistant for the Antwerp real estate market, hosted at **where.sweatlana.live**.

Scrapes Belgian portals (Immoweb, Immoscoop, Zimmo, Realo, Immovlan), stores versioned listings in SQLite, scores them against a per-user home-buyer config, and displays results in a Vue 3 + FastAPI web app with multi-user authentication.

---

## Running it

```bash
# Docker (production)
docker compose up --build

# Dev: backend
python -m uvicorn src.buyer.api:app --reload --host 0.0.0.0 --port 8000

# Dev: frontend
cd frontend && npm run dev
```

---

## Architecture

```
immowbot/
├── docker-compose.yml          # production deployment
├── Dockerfile
├── data/buyer.db               # SQLite store (auto-created)
├── src/
│   ├── base_scraper.py
│   ├── scraper_manager.py
│   ├── scrapers/               # immoweb, immoscoop, zimmo, realo, immovlan
│   └── buyer/
│       ├── api.py              # FastAPI app — all HTTP endpoints
│       ├── property_store.py   # SQLite — listings, users, lists, notes, workflow, alerts
│       ├── property_scoring.py # passes_hard_filters(), calculate_home_score()
│       ├── collector.py        # run_collection() — scraping pipeline
│       ├── scheduler.py        # daily run at 08:00
│       ├── search_config.py    # DEFAULT_HOME_SEARCH, normalize_search_config()
│       ├── smart_lists.py      # built-in smart list rules
│       ├── change_tracking.py  # diff_versions() — price/photo change detection
│       ├── property_explanation.py  # LLM-style property summary
│       ├── commute.py          # OSRM commute estimates
│       ├── duplicate_detection.py
│       └── purchase_calculator.py
├── frontend/
│   └── src/
│       ├── App.vue             # root: auth gate, routing (register/login/app)
│       ├── api.js              # all fetch calls to /api/*
│       ├── style.css
│       ├── components/
│       │   ├── Login.vue       # login form + quick access
│       │   ├── Register.vue    # invite-link registration
│       │   ├── Sidebar.vue     # search config, collection, account (change pwd, logout)
│       │   ├── DetailPanel.vue # property detail with image carousel
│       │   └── ...
│       └── views/
│           ├── Listings.vue    # Active tab
│           ├── Lists.vue
│           ├── Pipeline.vue
│           ├── History.vue
│           └── Duplicates.vue
└── tests/
```

---

## Authentication

Session cookies (HMAC-signed, 48h TTL). No JWT.

| Env var | Purpose | Default |
|---|---|---|
| `IMMOWBOT_AUTH_SECRET` | HMAC signing key | `change-me-in-production` |
| `IMMOWBOT_INVITE_TOKEN` | Secret token for invite-link registration | _(empty)_ |
| `IMMOWBOT_PASSWORD` | Initial password for `ampleyan` on first DB migration | `change-me` |

**Admin user:** `ampleyan` (created on first startup via DB migration).

**To invite a new user:** share `https://where.sweatlana.live/register/<IMMOWBOT_INVITE_TOKEN>`

**To create a user directly (admin API):**
```bash
curl -X POST https://where.sweatlana.live/api/users \
  -H "Content-Type: application/json" \
  -b "immowbot_session=<cookie>" \
  -d '{"username": "alice", "password": "securepass123", "is_admin": false}'
```

---

## Multi-user data model

All user data is scoped by `user_id`:
- `searches` — per-user search config
- `smart_lists` — per-user smart list rules
- `property_lists` — per-user manual lists
- `listing_workflow` — per-user pipeline status per property
- `property_notes` — per-user notes
- `alerts` — per-user price/photo change alerts
- `listing_interactions` — per-user contact log

Global (shared): `listings`, `listing_versions` (the scraped property catalogue).

---

## API surface (key endpoints)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | public | username + password |
| GET | `/api/auth/trusted` | public | returns `{"trusted": bool}` |
| POST | `/api/auth/login-trusted` | public | one-click login from any IP |
| GET | `/api/register/{token}` | public | validate invite token |
| POST | `/api/register/{token}` | public | create account via invite |
| GET | `/api/auth/me` | public | returns user if logged in |
| POST | `/api/auth/logout` | any | clear session |
| PUT | `/api/users/me/password` | any | change own password |
| GET | `/api/users` | admin | list all users |
| POST | `/api/users` | admin | create user directly |
| DELETE | `/api/users/{id}` | admin | delete user |
| GET | `/api/listings` | any | scored + filtered listings for current user |
| GET/PUT | `/api/config` | any | per-user search config |
| POST | `/api/runs` | any | start collection run |
| GET | `/api/runs/stream` | any | SSE progress stream |

---

## PropertyStore API (for Python callers)

```python
store = PropertyStore("data/buyer.db")

# Users
store.create_user(username, password, is_admin=False)  → user_id
store.authenticate_user(username, password)             → user dict or None
store.update_user_password(user_id, new_password)

# Search config (per user)
store.save_search(user_id, name, purpose, config)  → search_id
store.get_search(search_id)                        → {"config": {...}}
store.get_search_by_name(user_id, name)

# Listings (global catalogue)
run_id = store.start_run(search_id)
store.save_listing(run_id, canonical_dict)
store.finish_run(run_id, "ok")
store.latest_listings("sale")  → list of dicts
```

---

## Scraper quirks

**Immoweb:** uses `undetected-chromedriver` if available; CAPTCHA only triggers on "just a moment" title or `captcha-delivery.com` iframe.

**Immoscoop:** search URL `https://www.immoscoop.be/en/search/query?offerType=for-sale&...`; detail from `__NEXT_DATA__`.

**Zimmo:** detail from `<script id="ng-state">` JSON; bedrooms = count of `BEDROOM` items in `layout[]`.

**Realo / Immovlan:** JSON-LD structured data.

---

## Environment

- Python 3.12, Windows 11, Chrome 152
- Node 18+, Vite 8
- DB: `data/buyer.db` (auto-created)
- Tests: `python -m pytest tests/ -v`
