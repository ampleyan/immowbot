# Immowbot Buyer — Codex Handoff

## What this project is

A property buyer assistant for the Antwerp real estate market. It scrapes three Belgian portals
(Immoweb, Immoscoop, Zimmo), stores versioned listings in SQLite, scores them against a home-buyer
config, and shows results in a Streamlit dashboard.

---

## Current state (2026-09-13)

### Done

| Phase | What | Status |
|-------|------|--------|
| 1 | `search_config`, `property_store`, `property_scoring` + 14 tests | **Complete** |
| 2 | `collector` wiring scrapers through PropertyStore | **Complete** |
| 2.5 | Scraper audit + all three portals fixed | **Complete** |
| 3 | Streamlit dashboard | **Complete** |
| 4 | Daily scheduler + end-to-end verification | **TODO** |

### All tests pass

```
python -m pytest tests/ -v   # 14 tests, 0 failures
```

### Dashboard is live

```
python run_dashboard.py       # opens http://localhost:8501
```

---

## File map

```
immowbot/
├── run_dashboard.py               # launch: python run_dashboard.py
├── data/buyer.db                  # SQLite store (created on first run)
├── src/
│   ├── base_scraper.py            # abstract base; _normalize_epc_label(), _setup_chrome_driver()
│   ├── scraper_manager.py         # ScraperManager.scrape_website(website, max_price, ...)
│   ├── scrapers/
│   │   ├── immoweb_scraper.py     # uses undetected-chromedriver if available; CAPTCHA fix
│   │   ├── immoscoop_scraper.py   # /en/search/query?offerType=for-sale&... format
│   │   └── zimmo_scraper.py       # reads ng-state JSON; _parse_ng_state()
│   └── buyer/
│       ├── __init__.py
│       ├── search_config.py       # DEFAULT_HOME_SEARCH, normalize_search_config()
│       ├── property_store.py      # PropertyStore(path) — SQLite, versioned listings
│       ├── property_scoring.py    # passes_hard_filters(), calculate_home_score()
│       ├── collector.py           # run_collection(store, search_id, scraper_manager)
│       └── dashboard.py           # Streamlit app
└── tests/
    ├── test_property_store.py     # 6 tests
    ├── test_property_scoring.py   # 4 tests
    └── test_collector.py          # 4 tests
```

---

## Phase 4: What Codex needs to build

### 4a — Scheduler

Create `src/buyer/scheduler.py` that runs collection on a daily schedule.

**Requirements:**
- Use Python `schedule` library (add to requirements.txt)
- Run `run_collection(store, search_id, scraper_manager)` once per day at a configurable time
- Log start/end/errors to stdout with timestamps
- Keep running until killed (Ctrl-C)
- Entry point: `python -m src.buyer.scheduler` or `python run_scheduler.py`

**Suggested implementation:**
```python
import schedule, time, logging
from src.buyer.property_store import PropertyStore
from src.buyer.collector import run_collection
from src.scraper_manager import ScraperManager
from src.buyer.search_config import DEFAULT_HOME_SEARCH

DB_PATH = "data/buyer.db"
SEARCH_NAME = "antwerp-home"
RUN_AT = "08:00"

def job():
    store = PropertyStore(DB_PATH)
    search_id = ... # get or create search
    manager = ScraperManager()
    run_id = run_collection(store, search_id, manager)
    store.close()
    logging.info(f"Run {run_id} complete")

schedule.every().day.at(RUN_AT).do(job)
while True:
    schedule.run_pending()
    time.sleep(60)
```

Also add `run_scheduler.py` at project root (same pattern as `run_dashboard.py`).

### 4b — End-to-end smoke test

Create `tests/test_e2e_smoke.py` that:
1. Creates a temp SQLite store
2. Creates a search
3. Calls `run_collection` with a `FakeScraper` that returns 3 known listings
4. Asserts listings are in the store
5. Asserts `latest_listings("sale")` returns those listings
6. Asserts scores are computed correctly for them

This is different from existing unit tests — it exercises the full pipeline from scraper output through store through scoring.

### 4c — Dashboard UX improvements (optional, lower priority)

- Auto-refresh toggle (every N minutes, using `st.rerun()` + `time.sleep`)
- `st.dataframe` instead of manual column layout for the listings table (cleaner, sortable)
- "New since last run" badge on listings first seen in the most recent run
- Map view using `st.map` with latitude/longitude from listings (Immoweb and Zimmo provide coords)

---

## Key technical facts Codex must know

### Python style rules (from CLAUDE.md)
- Python 3.12, no type annotations, no inline comments

### EPC normalization
- All scrapers call `self._normalize_epc_label(value)` from `base_scraper.py`
- Returns one of: `"A++"`, `"A+"`, `"A"`, `"B"`, `"C"`, `"D"`, `"E"`, `"F"`, `"G"`, `""`
- kWh strings (e.g. `"264 kWh/m²"`) are discarded — return `""`

### PropertyStore API
```python
store = PropertyStore("data/buyer.db")
search_id = store.save_search("name", "home", config_dict)
run_id = store.start_run(search_id)
store.save_listing(run_id, canonical_listing)   # raises ValueError if required fields missing
store.record_source_result(run_id, "immoweb", "ok", count)
store.finish_run(run_id, "ok")                  # or "partial"
listings = store.latest_listings("sale")        # list of dicts
```

Required canonical listing fields: `source`, `source_listing_id`, `url`, `transaction_type`,
`price`, `postcode`, `property_type`, `surface_area`, `bedrooms`, `epc_score`

### Scraper manager API
```python
from src.scraper_manager import ScraperManager
manager = ScraperManager()
raw_listings = manager.scrape_website(
    website="immoweb",   # "immoweb" | "immoscoop" | "zimmo"
    max_price=385000,
    min_surface=80,
    epc_scores=["A", "B", "C"],
    postal_codes=["2000", "2018"],
    max_pages=5,
)
```

### Collector canonical mapping
`_to_canonical(raw, source)` in `collector.py` maps scraper output to canonical fields.
`source_listing_id` comes from `raw["id"]` falling back to `raw["url"]`.

### Default search config
```python
DEFAULT_HOME_SEARCH = {
    "postcodes": ["2000", "2018"],
    "property_types": ["house", "apartment"],
    "min_price": None,
    "max_price": 385000,
    "min_surface_area": 80,
    "min_bedrooms": 2,
    "epc_labels": ["A", "B", "C"],
    "portals": ["immoweb", "immoscoop", "zimmo"],
    "max_pages": 5,
}
```

### Scoring
- `passes_hard_filters(listing, config)` → bool
- `calculate_home_score(listing, config)` → `{"score": 0-100, "components": {...}, "exclusions": [...]}`
- Score is None and `exclusions: ["hard_filters"]` when listing fails hard filters
- Score components: price(30), surface_area(25), bedrooms(15), epc(20), completeness(10)

### Known scraper quirks

**Immoweb:**
- Uses `undetected-chromedriver` if available (bypasses Cloudflare); falls back to standard headless Chrome
- `_check_for_captcha` only triggers on page title "just a moment" or iframe src `captcha-delivery.com`
- UC needs `version_main=<chrome_major>` — detected via `_detect_chrome_version()` checking common Chrome install paths

**Immoscoop:**
- Search URL: `https://www.immoscoop.be/en/search/query?offerType=for-sale&postalCodes=2000,2018&...`
- Card selector: `[data-selector='property-card:card:vertical']`
- Detail pages use Next.js `__NEXT_DATA__` in HTML (fallback to parsing the embedded JSON from page source)

**Zimmo:**
- Search URL is a hardcoded base64-encoded JSON blob in `scrape_with_filters` (Antwerp A/B/C filter)
- Detail pages embed `<script id="ng-state" type="application/json">` with full property data
- `_parse_ng_state(soup, url)` extracts all fields; CSS selectors are stale fallback
- Bedroom count: count `layout[]` items where `spaceType == "BEDROOM"`
- EPC label: `estate.certificate.epcCertificate.energyLabel`

### Environment
- Python 3.12, Windows 11, Chrome 152
- Virtual env: `.venv/`
- DB: `data/buyer.db` (created automatically)
- Run tests: `python -m pytest tests/ -v`
- Run dashboard: `python run_dashboard.py`

---

## Commits this session (most recent first)

```
66a0f64 feat: streamlit buyer dashboard (Phase 3)
1c32ceb fix: immoweb captcha false-positive and zimmo stale selectors
1fdd79d fix: immoscoop search URL format and card selector
be661a5 fix: scraper robustness — ChromeDriver, EPC, postcode, Zimmo field extraction
9b4f89d fix: normalize EPC to letter label across all scrapers
7180573 feat: add portal collection layer (Phase 2)
23e399f feat: add property buyer core (Phase 1)
c2f51b0 chore: delete dead code from old scraper era
```
