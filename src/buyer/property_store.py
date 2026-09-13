import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from src.buyer.search_config import normalize_search_config

REQUIRED_LISTING_FIELDS = (
    "source", "source_listing_id", "url", "transaction_type",
    "price", "postcode", "property_type", "surface_area", "bedrooms", "epc_score",
)

_SCHEMA = """
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
"""


class PropertyStore:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(_SCHEMA)

    def save_search(self, name, purpose, config):
        normalized = normalize_search_config(config)
        config_json = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        with self.connection:
            self.connection.execute(
                """INSERT INTO searches (name, purpose, config_json)
                   VALUES (?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       purpose = excluded.purpose,
                       config_json = excluded.config_json""",
                (name, purpose, config_json),
            )
        return self.connection.execute(
            "SELECT id FROM searches WHERE name = ?", (name,)
        ).fetchone()["id"]

    def get_search(self, search_id):
        row = self.connection.execute(
            "SELECT * FROM searches WHERE id = ?", (search_id,)
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["config"] = json.loads(result.pop("config_json"))
        return result

    def list_searches(self, active=None):
        if active is None:
            rows = self.connection.execute("SELECT * FROM searches").fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM searches WHERE active = ?", (1 if active else 0,)
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["config"] = json.loads(item.pop("config_json"))
            results.append(item)
        return results

    def start_run(self, search_id):
        search = self.get_search(search_id)
        config_json = json.dumps(search["config"], ensure_ascii=False, sort_keys=True)
        started_at = datetime.now(timezone.utc).isoformat()
        with self.connection:
            cursor = self.connection.execute(
                """INSERT INTO runs (search_id, config_json, started_at, status)
                   VALUES (?, ?, ?, 'running')""",
                (search_id, config_json, started_at),
            )
        return cursor.lastrowid

    def get_run(self, run_id):
        row = self.connection.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["config"] = json.loads(result.pop("config_json"))
        return result

    def record_source_result(self, run_id, source, status, listing_count, error=None):
        with self.connection:
            self.connection.execute(
                """INSERT INTO source_runs (run_id, source, status, listing_count, error)
                   VALUES (?, ?, ?, ?, ?)""",
                (run_id, source, status, listing_count, error),
            )

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

    def finish_run(self, run_id, status):
        completed_at = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                "UPDATE runs SET status = ?, completed_at = ? WHERE id = ?",
                (status, completed_at, run_id),
            )

    def latest_listings(self, transaction_type):
        rows = self.connection.execute(
            """SELECT lv.payload_json
               FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.transaction_type = ?
               AND lv.id = (
                   SELECT MAX(lv2.id) FROM listing_versions lv2 WHERE lv2.listing_id = lv.listing_id
               )""",
            (transaction_type,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def version_count(self, source, source_listing_id):
        row = self.connection.execute(
            """SELECT COUNT(*) as cnt FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.source = ? AND l.source_listing_id = ?""",
            (source, str(source_listing_id)),
        ).fetchone()
        return row["cnt"]

    def close(self):
        self.connection.close()
