# Antwerp Property Buyer Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the configurable search, versioned SQLite storage, hard filtering, home scoring, and rental-yield scoring that every later collector and dashboard feature will use.

**Architecture:** `search_config.py` owns validation and first-run defaults, `property_store.py` is the only persistence boundary, and `property_scoring.py` contains deterministic pure functions. This phase creates five files and does not modify the user's current scraper work.

**Tech Stack:** Python 3.12, standard-library `sqlite3`, `hashlib`, `json`, `statistics`, and `unittest`

**Spec:** `docs/superpowers/specs/2026-09-13-antwerp-property-buyer-design.md`

## Global Constraints

- Default search: postcodes 2000 and 2018; houses and apartments; maximum EUR385,000; minimum two bedrooms; minimum 80 square metres; EPC A, B, or C.
- Search postcodes, property types, price bounds, minimum area, minimum bedrooms, EPC labels, enabled portals, and page limit are configurable and saved per profile.
- Missing required listing data fails the hard filter; values are never inferred.
- Listing versions and run configuration snapshots are immutable.
- Python code has no type annotations and no inline comments.
- Existing unrelated working-tree changes remain untouched.
- Stop after Phase 1 verification and request approval before planning or implementing collector changes.

---

### Task 1: Normalize configurable searches

**Files:**
- Create: `src/search_config.py`
- Create: `tests/test_property_store.py`

**Interfaces:**
- Produces: `AVAILABLE_PORTALS`, `DEFAULT_HOME_SEARCH`, `DEFAULT_INVESTMENT_SEARCH`, and `normalize_search_config(data)`.
- `normalize_search_config` returns a new dictionary and never mutates its input.

- [ ] **Step 1: Write the failing configuration tests**

```python
import os
import tempfile
import unittest

from src.search_config import DEFAULT_HOME_SEARCH, normalize_search_config


class SearchConfigTest(unittest.TestCase):
    def test_defaults_match_the_approved_search(self):
        config = normalize_search_config(DEFAULT_HOME_SEARCH)
        self.assertEqual(config["postcodes"], ["2000", "2018"])
        self.assertEqual(config["property_types"], ["house", "apartment"])
        self.assertEqual(config["max_price"], 385000)
        self.assertEqual(config["min_surface_area"], 80)
        self.assertEqual(config["min_bedrooms"], 2)
        self.assertEqual(config["epc_labels"], ["A", "B", "C"])

    def test_normalization_does_not_mutate_the_input(self):
        original = {**DEFAULT_HOME_SEARCH, "postcodes": [" 2018 ", "2000", "2018"]}
        config = normalize_search_config(original)
        self.assertEqual(config["postcodes"], ["2018", "2000"])
        self.assertEqual(original["postcodes"], [" 2018 ", "2000", "2018"])

    def test_invalid_ranges_and_portals_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_search_config({**DEFAULT_HOME_SEARCH, "min_price": 400000, "max_price": 300000})
        with self.assertRaises(ValueError):
            normalize_search_config({**DEFAULT_HOME_SEARCH, "portals": ["unknown"]})
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `python -m unittest tests.test_property_store.SearchConfigTest -v`

Expected: import failure for `src.search_config`.

- [ ] **Step 3: Implement the search configuration boundary**

```python
AVAILABLE_PORTALS = ("immoweb", "immoscoop", "zimmo")

DEFAULT_HOME_SEARCH = {
    "postcodes": ["2000", "2018"],
    "property_types": ["house", "apartment"],
    "min_price": None,
    "max_price": 385000,
    "min_surface_area": 80,
    "min_bedrooms": 2,
    "epc_labels": ["A", "B", "C"],
    "portals": list(AVAILABLE_PORTALS),
    "max_pages": 5,
}

DEFAULT_INVESTMENT_SEARCH = {
    **DEFAULT_HOME_SEARCH,
    "postcodes": list(DEFAULT_HOME_SEARCH["postcodes"]),
    "property_types": list(DEFAULT_HOME_SEARCH["property_types"]),
    "epc_labels": list(DEFAULT_HOME_SEARCH["epc_labels"]),
    "portals": list(DEFAULT_HOME_SEARCH["portals"]),
}


def normalize_search_config(data):
    config = dict(data)
    config["postcodes"] = list(dict.fromkeys(str(value).strip() for value in data.get("postcodes", [])))
    config["property_types"] = list(dict.fromkeys(str(value).strip().lower() for value in data.get("property_types", [])))
    config["epc_labels"] = list(dict.fromkeys(str(value).strip().upper() for value in data.get("epc_labels", [])))
    config["portals"] = list(dict.fromkeys(str(value).strip().lower() for value in data.get("portals", [])))
    for key in ("min_price", "max_price", "min_surface_area", "min_bedrooms", "max_pages"):
        value = data.get(key)
        config[key] = None if value in (None, "") else int(value)
    if not config["postcodes"] or any(len(value) != 4 or not value.isdigit() for value in config["postcodes"]):
        raise ValueError("postcodes must contain four-digit Belgian postcodes")
    if not config["property_types"]:
        raise ValueError("property_types cannot be empty")
    if not config["portals"] or any(value not in AVAILABLE_PORTALS for value in config["portals"]):
        raise ValueError("portals must contain supported portal names")
    if config["max_pages"] is None or config["max_pages"] < 1:
        raise ValueError("max_pages must be at least 1")
    for key in ("min_price", "max_price", "min_surface_area", "min_bedrooms"):
        if config[key] is not None and config[key] < 0:
            raise ValueError(f"{key} cannot be negative")
    if config["min_price"] is not None and config["max_price"] is not None and config["min_price"] > config["max_price"]:
        raise ValueError("min_price cannot exceed max_price")
    return config
```

- [ ] **Step 4: Run the configuration tests**

Run: `python -m unittest tests.test_property_store.SearchConfigTest -v`

Expected: three tests pass.

### Task 2: Persist searches, runs, source results, and listing versions

**Files:**
- Create: `src/property_store.py`
- Modify: `tests/test_property_store.py`

**Interfaces:**
- Produces: `PropertyStore(path)`.
- Public methods: `save_search(name, purpose, config)`, `get_search(search_id)`, `get_run(run_id)`, `list_searches(active=None)`, `start_run(search_id)`, `record_source_result(run_id, source, status, listing_count, error)`, `save_listing(run_id, listing)`, `finish_run(run_id, status)`, `latest_listings(transaction_type)`, `version_count(source, source_listing_id)`, and `close()`.
- A listing requires `source`, `source_listing_id`, `url`, `transaction_type`, `price`, `postcode`, `property_type`, `surface_area`, `bedrooms`, and `epc_score`; extra source fields remain in its JSON payload.

- [ ] **Step 1: Add failing persistence tests**

```python
from src.property_store import PropertyStore


class PropertyStoreTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        self.store = PropertyStore(self.path)

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_search_and_run_keep_normalized_configuration(self):
        search_id = self.store.save_search("home", "home", DEFAULT_HOME_SEARCH)
        search = self.store.get_search(search_id)
        run_id = self.store.start_run(search_id)
        self.assertEqual(search["config"]["max_price"], 385000)
        self.assertEqual(self.store.get_run(run_id)["config"], search["config"])

    def test_identical_observation_does_not_create_a_version(self):
        run_id = self._start_run()
        listing = self._listing()
        self.store.save_listing(run_id, listing)
        self.store.save_listing(run_id, listing)
        self.assertEqual(self.store.version_count("immoweb", "123"), 1)

    def test_changed_observation_creates_a_version(self):
        run_id = self._start_run()
        listing = self._listing()
        self.store.save_listing(run_id, listing)
        self.store.save_listing(run_id, {**listing, "price": 290000})
        self.assertEqual(self.store.version_count("immoweb", "123"), 2)
        self.assertEqual(self.store.latest_listings("sale")[0]["price"], 290000)

    def _start_run(self):
        search_id = self.store.save_search("home", "home", DEFAULT_HOME_SEARCH)
        return self.store.start_run(search_id)

    def _listing(self):
        return {
            "source": "immoweb",
            "source_listing_id": "123",
            "url": "https://example.test/123",
            "transaction_type": "sale",
            "price": 300000,
            "postcode": "2000",
            "property_type": "apartment",
            "surface_area": 90,
            "bedrooms": 2,
            "epc_score": "B",
        }
```

- [ ] **Step 2: Run the persistence tests and confirm they fail**

Run: `python -m unittest tests.test_property_store.PropertyStoreTest -v`

Expected: import failure for `src.property_store`.

- [ ] **Step 3: Create the SQLite schema at store initialization**

```sql
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    purpose TEXT NOT NULL CHECK (purpose IN ('home', 'investment')),
    config_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    search_id INTEGER NOT NULL REFERENCES searches(id),
    config_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_runs (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    listing_count INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    url TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('sale', 'rent')),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE(source, source_listing_id)
);
CREATE TABLE IF NOT EXISTS listing_versions (
    id INTEGER PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    run_id INTEGER NOT NULL REFERENCES runs(id),
    observed_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE(listing_id, content_hash)
);
```

- [ ] **Step 4: Implement JSON serialization and version insertion**

```python
def save_listing(self, run_id, listing):
    missing = [key for key in REQUIRED_LISTING_FIELDS if listing.get(key) in (None, "")]
    if missing:
        raise ValueError(f"listing missing required fields: {', '.join(missing)}")
    observed_at = datetime.now(timezone.utc).isoformat()
    payload_json = json.dumps(listing, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    content_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    with self.connection:
        self.connection.execute(
            """INSERT INTO listings
               (source, source_listing_id, url, transaction_type, first_seen_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(source, source_listing_id) DO UPDATE SET
                   url = excluded.url,
                   transaction_type = excluded.transaction_type,
                   last_seen_at = excluded.last_seen_at""",
            (listing["source"], str(listing["source_listing_id"]), listing["url"],
             listing["transaction_type"], observed_at, observed_at),
        )
        listing_id = self.connection.execute(
            "SELECT id FROM listings WHERE source = ? AND source_listing_id = ?",
            (listing["source"], str(listing["source_listing_id"])),
        ).fetchone()["id"]
        self.connection.execute(
            """INSERT OR IGNORE INTO listing_versions
               (listing_id, run_id, observed_at, content_hash, payload_json)
               VALUES (?, ?, ?, ?, ?)""",
            (listing_id, run_id, observed_at, content_hash, payload_json),
        )
    return listing_id
```

Implement the other public methods with parameterized SQL and `normalize_search_config`. `save_search` uses `ON CONFLICT(name) DO UPDATE`; `start_run` copies the saved `config_json`; `latest_listings` selects the greatest version ID for every listing of the requested transaction type and JSON-decodes it; reads return ordinary dictionaries.

- [ ] **Step 5: Run the storage tests and commit Tasks 1–2**

Run: `python -m unittest tests.test_property_store -v`

Expected: six tests pass.

Run: `git add src/search_config.py src/property_store.py tests/test_property_store.py`

Run: `git commit -m "feat: add buyer search storage"`

### Task 3: Apply hard filters and transparent scores

**Files:**
- Create: `src/property_scoring.py`
- Create: `tests/test_property_scoring.py`

**Interfaces:**
- Produces: `passes_hard_filters(listing, config)`, `calculate_home_score(listing, config)`, `select_rent_comparables(listing, rentals)`, and `calculate_investment_score(listing, config, rentals)`.
- Score functions return `{"score": number, "components": dict, "exclusions": list}` for qualifying listings and `{"score": None, "components": {}, "exclusions": list}` for excluded listings.

- [ ] **Step 1: Write the failing scoring tests**

```python
import unittest

from src.property_scoring import calculate_home_score, calculate_investment_score, passes_hard_filters
from src.search_config import DEFAULT_HOME_SEARCH


class PropertyScoringTest(unittest.TestCase):
    def setUp(self):
        self.sale = {
            "postcode": "2018",
            "property_type": "apartment",
            "price": 300000,
            "surface_area": 100,
            "bedrooms": 2,
            "epc_score": "B",
            "url": "https://example.test/sale",
        }
        self.rentals = [
            {"postcode": "2018", "property_type": "apartment", "surface_area": 95, "bedrooms": 2, "price": 1200},
            {"postcode": "2018", "property_type": "apartment", "surface_area": 105, "bedrooms": 3, "price": 1300},
            {"postcode": "2000", "property_type": "house", "surface_area": 100, "bedrooms": 2, "price": 2200},
        ]

    def test_hard_filters_reject_missing_or_unaccepted_epc(self):
        self.assertFalse(passes_hard_filters({**self.sale, "epc_score": None}, DEFAULT_HOME_SEARCH))
        self.assertFalse(passes_hard_filters({**self.sale, "epc_score": "D"}, DEFAULT_HOME_SEARCH))

    def test_home_score_is_bounded_and_explained(self):
        result = calculate_home_score(self.sale, DEFAULT_HOME_SEARCH)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertEqual(set(result["components"]), {"price", "surface_area", "bedrooms", "epc", "completeness"})

    def test_investment_score_exposes_comparable_evidence(self):
        result = calculate_investment_score(self.sale, DEFAULT_HOME_SEARCH, self.rentals)
        self.assertEqual(result["components"]["comparable_count"], 2)
        self.assertEqual(result["components"]["median_monthly_rent"], 1250)
        self.assertEqual(result["components"]["gross_yield_percent"], 5.0)

    def test_missing_comparables_do_not_fabricate_yield(self):
        result = calculate_investment_score(self.sale, DEFAULT_HOME_SEARCH, [])
        self.assertIsNone(result["components"]["median_monthly_rent"])
        self.assertIsNone(result["components"]["gross_yield_percent"])
```

- [ ] **Step 2: Run the scoring tests and confirm they fail**

Run: `python -m unittest tests.test_property_scoring -v`

Expected: import failure for `src.property_scoring`.

- [ ] **Step 3: Implement deterministic score helpers**

```python
from statistics import median


EPC_FACTOR = {
    "A++": 1.0,
    "A+": 1.0,
    "A": 1.0,
    "B": 0.7,
    "C": 0.4,
    "D": 0.25,
    "E": 0.15,
    "F": 0.05,
    "G": 0.0,
}
COMPLETENESS_FIELDS = ("price", "postcode", "property_type", "surface_area", "bedrooms", "epc_score", "url")


def _ratio_above_minimum(value, minimum):
    if not minimum:
        return 1.0
    return min(max((value - minimum) / minimum, 0.0), 1.0)


def _price_headroom(price, maximum):
    if not maximum:
        return 1.0
    return min(max((maximum - price) / maximum, 0.0), 1.0)


def _completeness(listing):
    present = sum(listing.get(key) not in (None, "") for key in COMPLETENESS_FIELDS)
    return present / len(COMPLETENESS_FIELDS)


def _epc_label(value):
    text = str(value or "").strip().upper()
    return next((label for label in ("A++", "A+", "A", "B", "C", "D", "E", "F", "G") if text.startswith(label)), "")
```

- [ ] **Step 4: Implement hard filters, comparable selection, and score assembly**

```python
def passes_hard_filters(listing, config):
    required = ("postcode", "property_type", "price", "surface_area", "bedrooms", "epc_score")
    if any(listing.get(key) in (None, "") for key in required):
        return False
    return (
        str(listing["postcode"]) in config["postcodes"]
        and str(listing["property_type"]).lower() in config["property_types"]
        and (config["min_price"] is None or listing["price"] >= config["min_price"])
        and (config["max_price"] is None or listing["price"] <= config["max_price"])
        and (config["min_surface_area"] is None or listing["surface_area"] >= config["min_surface_area"])
        and (config["min_bedrooms"] is None or listing["bedrooms"] >= config["min_bedrooms"])
        and _epc_label(listing["epc_score"]) in config["epc_labels"]
    )


def calculate_home_score(listing, config):
    if not passes_hard_filters(listing, config):
        return {"score": None, "components": {}, "exclusions": ["hard_filters"]}
    components = {
        "price": 30 * _price_headroom(listing["price"], config["max_price"]),
        "surface_area": 25 * _ratio_above_minimum(listing["surface_area"], config["min_surface_area"]),
        "bedrooms": 15 * _ratio_above_minimum(listing["bedrooms"], config["min_bedrooms"]),
        "epc": 20 * EPC_FACTOR[_epc_label(listing["epc_score"])],
        "completeness": 10 * _completeness(listing),
    }
    components = {key: round(value, 2) for key, value in components.items()}
    return {"score": round(sum(components.values()), 2), "components": components, "exclusions": []}


def select_rent_comparables(listing, rentals):
    lower_area = listing["surface_area"] * 0.8
    upper_area = listing["surface_area"] * 1.2
    return [rental for rental in rentals if rental.get("postcode") == listing.get("postcode")
            and rental.get("property_type") == listing.get("property_type")
            and rental.get("surface_area") is not None and lower_area <= rental["surface_area"] <= upper_area
            and rental.get("bedrooms") is not None and abs(rental["bedrooms"] - listing["bedrooms"]) <= 1
            and rental.get("price", 0) > 0]


def calculate_investment_score(listing, config, rentals):
    if not passes_hard_filters(listing, config):
        return {"score": None, "components": {}, "exclusions": ["hard_filters"]}
    comparables = select_rent_comparables(listing, rentals)
    monthly_rent = median(item["price"] for item in comparables) if comparables else None
    gross_yield = monthly_rent * 12 / listing["price"] * 100 if monthly_rent is not None else None
    components = {
        "yield": round(50 * min(gross_yield / 6, 1), 2) if gross_yield is not None else 0,
        "epc": round(20 * EPC_FACTOR[_epc_label(listing["epc_score"])], 2),
        "price": round(15 * _price_headroom(listing["price"], config["max_price"]), 2),
        "completeness": round(15 * _completeness(listing), 2),
        "comparable_count": len(comparables),
        "median_monthly_rent": monthly_rent,
        "gross_yield_percent": round(gross_yield, 2) if gross_yield is not None else None,
    }
    scored_components = ("yield", "epc", "price", "completeness")
    return {"score": round(sum(components[key] for key in scored_components), 2), "components": components, "exclusions": []}
```

- [ ] **Step 5: Run all Phase 1 verification**

Run: `python -m unittest tests.test_property_store tests.test_property_scoring -v`

Expected: ten tests pass.

Run: `python -m compileall src tests`

Expected: successful compilation. The repository has no configured Python type checker or linter, so record that explicitly.

Run: `git diff --check`

Expected: no whitespace errors introduced by Phase 1 files.

- [ ] **Step 6: Re-read the five Phase 1 files, commit, and stop**

Confirm no removed name is referenced and no Phase 1 file contains an unused import or inline comment.

Run: `git add src/search_config.py src/property_store.py src/property_scoring.py tests/test_property_store.py tests/test_property_scoring.py`

Run: `git commit -m "feat: add property buyer core"`

Report the exact test and compilation results, then wait for explicit approval before Phase 2.
