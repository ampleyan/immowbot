import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import datetime, timezone

from src.buyer.search_config import normalize_search_config

REQUIRED_LISTING_FIELDS = (
    "source", "source_listing_id", "url", "transaction_type", "price", "postcode",
)

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS property_lists (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, name)
);
CREATE TABLE IF NOT EXISTS list_items (
    id INTEGER PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES property_lists(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE(list_id, source, source_listing_id)
);
CREATE TABLE IF NOT EXISTS property_notes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    note TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, source, source_listing_id)
);
CREATE TABLE IF NOT EXISTS listing_workflow (
    user_id INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'New',
    contact_date TEXT,
    next_follow_up_date TEXT,
    agent_name TEXT,
    agent_phone TEXT,
    agent_email TEXT,
    offer_amount REAL,
    rejection_reason TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, source, source_listing_id)
);
CREATE TABLE IF NOT EXISTS listing_interactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL,
    next_follow_up_date TEXT,
    UNIQUE(id)
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    url TEXT,
    created_at TEXT NOT NULL,
    read_at TEXT,
    UNIQUE(user_id, source, source_listing_id, kind)
);
CREATE TABLE IF NOT EXISTS smart_lists (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    rule_json TEXT NOT NULL,
    is_system INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, name)
);
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('home', 'investment')),
    config_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id, name)
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


def _hash_password(password):
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), 260000)
    return f"pbkdf2:sha256:260000:{salt}:{dk.hex()}"


def _verify_password(password, password_hash):
    try:
        _, alg, iterations, salt, stored_dk = password_hash.split(":", 4)
        dk = hashlib.pbkdf2_hmac(alg, password.encode("utf-8"), salt.encode(), int(iterations))
        return hmac.compare_digest(dk.hex(), stored_dk)
    except Exception:
        return False


class PropertyStore:
    def __init__(self, path):
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=30000")
        self.connection.executescript(_SCHEMA)
        self._run_user_migration()

    def _run_user_migration(self):
        cols = {r[1] for r in self.connection.execute("PRAGMA table_info(searches)")}
        if "user_id" in cols:
            self._repair_runs_foreign_key()
            return

        import os as _os
        self.connection.execute("PRAGMA foreign_keys = OFF")
        self.connection.execute("PRAGMA legacy_alter_table = ON")

        tables_to_recreate = [
            (
                "searches",
                """CREATE TABLE searches (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    name TEXT NOT NULL,
                    purpose TEXT NOT NULL CHECK (purpose IN ('home', 'investment')),
                    config_json TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(user_id, name)
                )""",
                "SELECT id, 1, name, purpose, config_json, active FROM searches",
            ),
            (
                "smart_lists",
                """CREATE TABLE smart_lists (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    name TEXT NOT NULL,
                    rule_json TEXT NOT NULL,
                    is_system INTEGER NOT NULL DEFAULT 0,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, name)
                )""",
                "SELECT id, 1, name, rule_json, is_system, enabled, created_at, updated_at FROM smart_lists",
            ),
            (
                "property_lists",
                """CREATE TABLE property_lists (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, name)
                )""",
                "SELECT id, 1, name, created_at FROM property_lists",
            ),
            (
                "listing_workflow",
                """CREATE TABLE listing_workflow (
                    user_id INTEGER NOT NULL DEFAULT 1,
                    source TEXT NOT NULL,
                    source_listing_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'New',
                    contact_date TEXT,
                    next_follow_up_date TEXT,
                    agent_name TEXT,
                    agent_phone TEXT,
                    agent_email TEXT,
                    offer_amount REAL,
                    rejection_reason TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, source, source_listing_id)
                )""",
                "SELECT 1, source, source_listing_id, status, contact_date, next_follow_up_date, agent_name, agent_phone, agent_email, offer_amount, COALESCE(rejection_reason, ''), updated_at FROM listing_workflow",
            ),
            (
                "property_notes",
                """CREATE TABLE property_notes (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    source TEXT NOT NULL,
                    source_listing_id TEXT NOT NULL,
                    note TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, source, source_listing_id)
                )""",
                "SELECT id, 1, source, source_listing_id, note, updated_at FROM property_notes",
            ),
            (
                "alerts",
                """CREATE TABLE alerts (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    source TEXT NOT NULL,
                    source_listing_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    message TEXT NOT NULL,
                    url TEXT,
                    created_at TEXT NOT NULL,
                    read_at TEXT,
                    UNIQUE(user_id, source, source_listing_id, kind)
                )""",
                "SELECT id, 1, source, source_listing_id, kind, message, url, created_at, read_at FROM alerts",
            ),
        ]

        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

            for table_name, create_sql, select_sql in tables_to_recreate:
                self.connection.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_old")
                self.connection.execute(create_sql)
                legacy_select_sql = select_sql.replace(
                    f"FROM {table_name}", f"FROM {table_name}_old"
                )
                self.connection.execute(f"INSERT INTO {table_name} SELECT * FROM ({legacy_select_sql})")
                self.connection.execute(f"DROP TABLE {table_name}_old")

            cols = {r[1] for r in self.connection.execute("PRAGMA table_info(listing_interactions)")}
            if "user_id" not in cols:
                self.connection.execute(
                    "ALTER TABLE listing_interactions ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1"
                )

            initial_password = _os.getenv("IMMOWBOT_PASSWORD", "change-me")
            pw_hash = _hash_password(initial_password)
            self.connection.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, 1, ?)",
                ("ampleyan", pw_hash, datetime.now(timezone.utc).isoformat()),
            )

        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA legacy_alter_table = OFF")
        print("[immowbot] Migration complete: all data assigned to user 'ampleyan' (admin)")
        print("[immowbot] Login: username=ampleyan  password=<IMMOWBOT_PASSWORD env var or 'change-me'>")

    def _repair_runs_foreign_key(self):
        foreign_keys = self.connection.execute("PRAGMA foreign_key_list(runs)").fetchall()
        if all(row[2] == "searches" for row in foreign_keys):
            return

        self.connection.execute("PRAGMA foreign_keys = OFF")
        self.connection.execute("PRAGMA legacy_alter_table = ON")
        try:
            with self.connection:
                self.connection.execute("ALTER TABLE runs RENAME TO runs_old")
                self.connection.execute("""
                    CREATE TABLE runs (
                        id INTEGER PRIMARY KEY,
                        search_id INTEGER NOT NULL REFERENCES searches(id),
                        config_json TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        completed_at TEXT,
                        status TEXT NOT NULL
                    )
                """)
                self.connection.execute("""
                    INSERT INTO runs (id, search_id, config_json, started_at, completed_at, status)
                    SELECT id, search_id, config_json, started_at, completed_at, status
                    FROM runs_old
                """)
                self.connection.execute("DROP TABLE runs_old")
        finally:
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA legacy_alter_table = OFF")

    def create_user(self, username, password, is_admin=False):
        username = str(username or "").strip()
        if not username:
            raise ValueError("username required")
        pw_hash = _hash_password(password or "")
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)",
                (username, pw_hash, 1 if is_admin else 0, now),
            )
        return cursor.lastrowid

    def get_user_by_username(self, username):
        row = self.connection.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id):
        row = self.connection.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def authenticate_user(self, username, password):
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not _verify_password(password, user["password_hash"]):
            return None
        return user

    def list_users(self):
        rows = self.connection.execute(
            "SELECT id, username, is_admin, created_at FROM users ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    def update_user_password(self, user_id, new_password):
        pw_hash = _hash_password(new_password or "")
        with self.connection:
            self.connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, user_id)
            )

    def delete_user(self, user_id):
        with self.connection:
            self.connection.execute("DELETE FROM users WHERE id = ?", (user_id,))

    def ensure_builtin_smart_lists(self, user_id, builtins):
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            for name, rule in builtins:
                self.connection.execute(
                    """INSERT INTO smart_lists (user_id, name, rule_json, is_system, created_at, updated_at)
                       VALUES (?, ?, ?, 1, ?, ?)
                       ON CONFLICT(user_id, name) DO UPDATE SET is_system = 1""",
                    (user_id, name, json.dumps(rule, sort_keys=True), now, now),
                )

    def get_smart_lists(self, user_id, enabled=None):
        query = "SELECT * FROM smart_lists WHERE user_id = ?"
        args = (user_id,)
        if enabled is not None:
            query += " AND enabled = ?"
            args = (user_id, 1 if enabled else 0)
        query += " ORDER BY is_system DESC, name"
        rows = self.connection.execute(query, args).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["rule"] = json.loads(item.pop("rule_json"))
            item["is_system"] = bool(item["is_system"])
            item["enabled"] = bool(item["enabled"])
            result.append(item)
        return result

    def create_smart_list(self, user_id, name, rule, is_system=False):
        name = str(name or "").strip()
        if not name:
            raise ValueError("name required")
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO smart_lists (user_id, name, rule_json, is_system, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, name, json.dumps(rule or {}, sort_keys=True), 1 if is_system else 0, now, now),
            )
        return cursor.lastrowid

    def update_smart_list(self, user_id, list_id, name, rule, enabled):
        row = self.connection.execute(
            "SELECT is_system, name FROM smart_lists WHERE id = ? AND user_id = ?", (list_id, user_id)
        ).fetchone()
        if row is None:
            return False
        if row["is_system"]:
            name = row["name"]
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                "UPDATE smart_lists SET name = ?, rule_json = ?, enabled = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (name, json.dumps(rule or {}, sort_keys=True), 1 if enabled else 0, now, list_id, user_id),
            )
        return True

    def delete_smart_list(self, user_id, list_id):
        row = self.connection.execute(
            "SELECT is_system FROM smart_lists WHERE id = ? AND user_id = ?", (list_id, user_id)
        ).fetchone()
        if row is None:
            return False
        if row["is_system"]:
            raise ValueError("system smart lists cannot be deleted")
        with self.connection:
            self.connection.execute("DELETE FROM smart_lists WHERE id = ? AND user_id = ?", (list_id, user_id))
        return True

    def save_search(self, user_id, name, purpose, config):
        normalized = normalize_search_config(config)
        config_json = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        with self.connection:
            self.connection.execute(
                """INSERT INTO searches (user_id, name, purpose, config_json)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, name) DO UPDATE SET
                       purpose = excluded.purpose,
                       config_json = excluded.config_json""",
                (user_id, name, purpose, config_json),
            )
        return self.connection.execute(
            "SELECT id FROM searches WHERE user_id = ? AND name = ?", (user_id, name)
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

    def get_search_by_name(self, user_id, name):
        row = self.connection.execute(
            "SELECT id FROM searches WHERE user_id = ? AND name = ?", (user_id, name)
        ).fetchone()
        return self.get_search(row["id"]) if row else None

    def list_searches(self, user_id, active=None):
        if active is None:
            rows = self.connection.execute(
                "SELECT * FROM searches WHERE user_id = ?", (user_id,)
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM searches WHERE user_id = ? AND active = ?", (user_id, 1 if active else 0)
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
        previous = self.connection.execute(
            """SELECT lv.payload_json FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.source = ? AND l.source_listing_id = ?
               ORDER BY lv.id DESC LIMIT 1""",
            (listing["source"], str(listing["source_listing_id"])),
        ).fetchone()
        if previous:
            previous_payload = json.loads(previous["payload_json"])
            images = []
            for payload in (previous_payload, listing):
                values = list(payload.get("images") or [])
                values.extend(payload.get(key) for key in ("image_url_1", "image_url_2"))
                for image in values:
                    if image not in (None, "") and image not in images:
                        images.append(image)
            if images:
                listing = {**listing, "images": images, "image_url_1": images[0], "image_url_2": images[1] if len(images) > 1 else None}
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
            """SELECT lv.payload_json, l.first_seen_at
               FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.transaction_type = ?
               AND lv.id = (
                   SELECT MAX(lv2.id) FROM listing_versions lv2 WHERE lv2.listing_id = lv.listing_id
               )""",
            (transaction_type,),
        ).fetchall()
        result = []
        for row in rows:
            item = json.loads(row["payload_json"])
            item["_first_seen_at"] = row["first_seen_at"]
            result.append(item)
        return result

    def listings_for_run(self, run_id):
        rows = self.connection.execute(
            """SELECT lv.payload_json, l.first_seen_at
               FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE lv.run_id = ?
               ORDER BY lv.id""",
            (run_id,),
        ).fetchall()
        result = []
        for row in rows:
            item = json.loads(row["payload_json"])
            item["_first_seen_at"] = row["first_seen_at"]
            result.append(item)
        return result

    def listing_history(self, source, source_listing_id):
        rows = self.connection.execute(
            """SELECT lv.observed_at, lv.payload_json, lv.id
               FROM listing_versions lv INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.source = ? AND l.source_listing_id = ? ORDER BY lv.id""",
            (source, str(source_listing_id)),
        ).fetchall()
        return [{"observed_at": row["observed_at"], "payload": json.loads(row["payload_json"])} for row in rows]

    def delete_listing(self, source, source_listing_id):
        with self.connection:
            row = self.connection.execute(
                "SELECT id FROM listings WHERE source = ? AND source_listing_id = ?",
                (source, str(source_listing_id)),
            ).fetchone()
            if row:
                lid = row["id"]
                self.connection.execute(
                    "DELETE FROM listing_versions WHERE listing_id = ?", (lid,)
                )
                self.connection.execute("DELETE FROM listings WHERE id = ?", (lid,))

    def merge_listing_payload(self, source, source_listing_id, payload):
        source_listing_id = str(source_listing_id)
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        content_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        with self.connection:
            row = self.connection.execute(
                """SELECT l.id, lv.run_id FROM listings l
                   INNER JOIN listing_versions lv ON lv.listing_id = l.id
                   WHERE l.source = ? AND l.source_listing_id = ?
                   ORDER BY lv.id DESC LIMIT 1""",
                (source, source_listing_id),
            ).fetchone()
            if not row:
                return
            self.connection.execute(
                """INSERT OR IGNORE INTO listing_versions
                   (listing_id, run_id, observed_at, content_hash, payload_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (row["id"], row["run_id"], datetime.now(timezone.utc).isoformat(), content_hash, payload_json),
            )

    def get_lists(self, user_id):
        rows = self.connection.execute(
            """SELECT pl.id, pl.name, pl.created_at, COUNT(li.id) as item_count
               FROM property_lists pl
               LEFT JOIN list_items li ON li.list_id = pl.id
               WHERE pl.user_id = ?
               GROUP BY pl.id ORDER BY pl.created_at""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def create_list(self, user_id, name):
        created_at = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO property_lists (user_id, name, created_at) VALUES (?, ?, ?)",
                (user_id, name.strip(), created_at),
            )
        return self.connection.execute(
            "SELECT id FROM property_lists WHERE user_id = ? AND name = ?", (user_id, name.strip())
        ).fetchone()["id"]

    def delete_list(self, user_id, list_id):
        with self.connection:
            self.connection.execute(
                "DELETE FROM property_lists WHERE id = ? AND user_id = ?", (list_id, user_id)
            )

    def add_to_list(self, user_id, list_id, source, source_listing_id):
        row = self.connection.execute(
            "SELECT id FROM property_lists WHERE id = ? AND user_id = ?", (list_id, user_id)
        ).fetchone()
        if not row:
            raise ValueError("list not found")
        added_at = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                """INSERT OR IGNORE INTO list_items (list_id, source, source_listing_id, added_at)
                   VALUES (?, ?, ?, ?)""",
                (list_id, source, str(source_listing_id), added_at),
            )

    def remove_from_list(self, user_id, list_id, source, source_listing_id):
        row = self.connection.execute(
            "SELECT id FROM property_lists WHERE id = ? AND user_id = ?", (list_id, user_id)
        ).fetchone()
        if not row:
            raise ValueError("list not found")
        with self.connection:
            self.connection.execute(
                "DELETE FROM list_items WHERE list_id = ? AND source = ? AND source_listing_id = ?",
                (list_id, source, str(source_listing_id)),
            )

    def get_list_items(self, user_id, list_id):
        row = self.connection.execute(
            "SELECT id FROM property_lists WHERE id = ? AND user_id = ?", (list_id, user_id)
        ).fetchone()
        if not row:
            return []
        rows = self.connection.execute(
            """SELECT lv.payload_json
               FROM list_items li
               INNER JOIN listings l ON l.source = li.source AND l.source_listing_id = li.source_listing_id
               INNER JOIN listing_versions lv ON lv.listing_id = l.id
               WHERE li.list_id = ?
               AND lv.id = (
                   SELECT MAX(lv2.id) FROM listing_versions lv2 WHERE lv2.listing_id = lv.listing_id
               )
               ORDER BY li.added_at""",
            (list_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def get_property_list_ids(self, user_id, source, source_listing_id):
        rows = self.connection.execute(
            """SELECT li.list_id FROM list_items li
               INNER JOIN property_lists pl ON pl.id = li.list_id
               WHERE li.source = ? AND li.source_listing_id = ? AND pl.user_id = ?""",
            (source, str(source_listing_id), user_id),
        ).fetchall()
        return {row["list_id"] for row in rows}

    def save_note(self, user_id, source, source_listing_id, note):
        updated_at = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                """INSERT INTO property_notes (user_id, source, source_listing_id, note, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, source, source_listing_id) DO UPDATE SET
                       note = excluded.note,
                       updated_at = excluded.updated_at""",
                (user_id, source, str(source_listing_id), note, updated_at),
            )

    def get_note(self, user_id, source, source_listing_id):
        row = self.connection.execute(
            "SELECT note FROM property_notes WHERE user_id = ? AND source = ? AND source_listing_id = ?",
            (user_id, source, str(source_listing_id)),
        ).fetchone()
        return row["note"] if row else ""

    def get_all_notes(self, user_id):
        rows = self.connection.execute(
            "SELECT source, source_listing_id, note FROM property_notes WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {(r["source"], r["source_listing_id"]): r["note"] for r in rows}

    def get_workflow(self, user_id, source, source_listing_id):
        row = self.connection.execute(
            "SELECT * FROM listing_workflow WHERE user_id = ? AND source = ? AND source_listing_id = ?",
            (user_id, source, str(source_listing_id)),
        ).fetchone()
        if row:
            return dict(row)
        return {
            "user_id": user_id,
            "source": source,
            "source_listing_id": str(source_listing_id),
            "status": "New",
            "contact_date": None,
            "next_follow_up_date": None,
            "agent_name": "",
            "agent_phone": "",
            "agent_email": "",
            "offer_amount": None,
            "rejection_reason": "",
        }

    def save_workflow(self, user_id, source, source_listing_id, data):
        allowed = ("status", "contact_date", "next_follow_up_date", "agent_name", "agent_phone", "agent_email", "offer_amount", "rejection_reason")
        values = {key: data.get(key) for key in allowed}
        values["status"] = values["status"] or "New"
        if values["status"] not in ("New", "Interested", "Contacted", "Visit planned", "Offer", "Rejected"):
            raise ValueError("invalid workflow status")
        previous = self.connection.execute(
            "SELECT status FROM listing_workflow WHERE user_id = ? AND source = ? AND source_listing_id = ?",
            (user_id, source, str(source_listing_id)),
        ).fetchone()
        updated_at = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                """INSERT INTO listing_workflow (user_id, source, source_listing_id, status, contact_date, next_follow_up_date, agent_name, agent_phone, agent_email, offer_amount, rejection_reason, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, source, source_listing_id) DO UPDATE SET status=excluded.status, contact_date=excluded.contact_date, next_follow_up_date=excluded.next_follow_up_date, agent_name=excluded.agent_name, agent_phone=excluded.agent_phone, agent_email=excluded.agent_email, offer_amount=excluded.offer_amount, rejection_reason=excluded.rejection_reason, updated_at=excluded.updated_at""",
                (user_id, source, str(source_listing_id), values["status"], values["contact_date"], values["next_follow_up_date"], values["agent_name"], values["agent_phone"], values["agent_email"], values["offer_amount"], values["rejection_reason"] or "", updated_at),
            )
            if (previous is None and values["status"] != "New") or (previous is not None and previous["status"] != values["status"]):
                self.connection.execute(
                    "INSERT INTO listing_interactions (user_id, source, source_listing_id, kind, note, occurred_at, next_follow_up_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, source, str(source_listing_id), "status", "Status changed to " + values["status"] + (": " + values["rejection_reason"] if values["status"] == "Rejected" and values["rejection_reason"] else ""), updated_at, values["next_follow_up_date"]),
                )
        return self.get_workflow(user_id, source, source_listing_id)

    def add_interaction(self, user_id, source, source_listing_id, kind, note="", occurred_at=None, next_follow_up_date=None):
        if kind not in ("call", "email", "message", "visit", "status", "other"):
            raise ValueError("invalid interaction kind")
        occurred_at = occurred_at or datetime.now(timezone.utc).isoformat()
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO listing_interactions (user_id, source, source_listing_id, kind, note, occurred_at, next_follow_up_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, source, str(source_listing_id), kind, (note or "").strip(), occurred_at, next_follow_up_date),
            )
        row = self.connection.execute(
            "SELECT * FROM listing_interactions WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    def get_interactions(self, user_id, source, source_listing_id):
        rows = self.connection.execute(
            "SELECT * FROM listing_interactions WHERE user_id = ? AND source = ? AND source_listing_id = ? ORDER BY occurred_at DESC, id DESC",
            (user_id, source, str(source_listing_id)),
        ).fetchall()
        return [dict(row) for row in rows]

    def version_count(self, source, source_listing_id):
        row = self.connection.execute(
            """SELECT COUNT(*) as cnt FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.source = ? AND l.source_listing_id = ?""",
            (source, str(source_listing_id)),
        ).fetchone()
        return row["cnt"]

    def add_alert(self, user_id, source, source_listing_id, kind, message, url):
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO alerts (user_id, source, source_listing_id, kind, message, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, source, str(source_listing_id), kind, message, url, datetime.now(timezone.utc).isoformat()),
            )

    def get_alerts(self, user_id):
        rows = self.connection.execute(
            "SELECT * FROM alerts WHERE user_id = ? ORDER BY id DESC LIMIT 100",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_alert_read(self, user_id, alert_id):
        with self.connection:
            self.connection.execute(
                "UPDATE alerts SET read_at = ? WHERE id = ? AND user_id = ?",
                (datetime.now(timezone.utc).isoformat(), alert_id, user_id),
            )

    def clear_alerts(self, user_id):
        with self.connection:
            self.connection.execute(
                "UPDATE alerts SET read_at = ? WHERE read_at IS NULL AND user_id = ?",
                (datetime.now(timezone.utc).isoformat(), user_id),
            )

    def close(self):
        self.connection.close()
