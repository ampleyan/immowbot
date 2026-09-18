import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from src.buyer.search_config import normalize_search_config

REQUIRED_LISTING_FIELDS = (
    "source", "source_listing_id", "url", "transaction_type", "price", "postcode",
)


def _normalized_listing_fingerprint(listing):
    """Hash stable listing content so formatting and image-order noise do not create history."""
    def normalize(value, key=None):
        if isinstance(value, dict):
            return {str(k): normalize(v, str(k)) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
        if isinstance(value, list):
            normalized = [normalize(item) for item in value]
            if key == "images":
                return sorted({json.dumps(item, ensure_ascii=False, sort_keys=True) for item in normalized})
            return normalized
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    payload = normalize({key: value for key, value in listing.items() if not str(key).startswith("_") and key not in {"description_english", "description_language"}})
    payload_str = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()


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


def to_dict(row):
    if row is None:
        return None
    result = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


class PropertyStore:
    def __init__(self, dsn):
        self.connection = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)

    def create_user(self, username, password, is_admin=False):
        username = str(username or "").strip()
        if not username:
            raise ValueError("username required")
        pw_hash = _hash_password(password or "")
        now = datetime.now(timezone.utc)
        with self.connection.transaction():
            cursor = self.connection.execute(
                "INSERT INTO users (username, password_hash, is_admin, created_at, alerts_since) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (username, pw_hash, is_admin, now, now),
            )
            return cursor.fetchone()["id"]

    def get_user_by_username(self, username):
        row = self.connection.execute(
            "SELECT * FROM users WHERE username = %s", (username,)
        ).fetchone()
        return to_dict(row)

    def get_user_by_id(self, user_id):
        row = self.connection.execute(
            "SELECT * FROM users WHERE id = %s", (user_id,)
        ).fetchone()
        return to_dict(row)

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
        return [to_dict(r) for r in rows]

    def update_user_password(self, user_id, new_password):
        pw_hash = _hash_password(new_password or "")
        with self.connection.transaction():
            self.connection.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s", (pw_hash, user_id)
            )

    def delete_user(self, user_id):
        with self.connection.transaction():
            self.connection.execute("DELETE FROM users WHERE id = %s", (user_id,))

    def ensure_builtin_smart_lists(self, user_id, builtins):
        now = datetime.now(timezone.utc)
        with self.connection.transaction():
            for name, rule in builtins:
                self.connection.execute(
                    """INSERT INTO smart_lists (user_id, name, rule_json, is_system, created_at, updated_at)
                       VALUES (%s, %s, %s, TRUE, %s, %s)
                       ON CONFLICT(user_id, name) DO UPDATE SET is_system = TRUE""",
                    (user_id, name, Jsonb(rule), now, now),
                )

    def get_smart_lists(self, user_id, enabled=None):
        query = "SELECT * FROM smart_lists WHERE user_id = %s"
        args = (user_id,)
        if enabled is not None:
            query += " AND enabled = %s"
            args = (user_id, bool(enabled))
        query += " ORDER BY is_system DESC, name"
        rows = self.connection.execute(query, args).fetchall()
        result = []
        for row in rows:
            item = to_dict(row)
            item["rule"] = item.pop("rule_json")
            item["is_system"] = bool(item["is_system"])
            item["enabled"] = bool(item["enabled"])
            result.append(item)
        return result

    def create_smart_list(self, user_id, name, rule, is_system=False):
        name = str(name or "").strip()
        if not name:
            raise ValueError("name required")
        now = datetime.now(timezone.utc)
        with self.connection.transaction():
            cursor = self.connection.execute(
                "INSERT INTO smart_lists (user_id, name, rule_json, is_system, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (user_id, name, Jsonb(rule or {}), is_system, now, now),
            )
            return cursor.fetchone()["id"]

    def update_smart_list(self, user_id, list_id, name, rule, enabled):
        row = self.connection.execute(
            "SELECT is_system, name FROM smart_lists WHERE id = %s AND user_id = %s", (list_id, user_id)
        ).fetchone()
        if row is None:
            return False
        if row["is_system"]:
            name = row["name"]
        now = datetime.now(timezone.utc)
        with self.connection.transaction():
            self.connection.execute(
                "UPDATE smart_lists SET name = %s, rule_json = %s, enabled = %s, updated_at = %s WHERE id = %s AND user_id = %s",
                (name, Jsonb(rule or {}), bool(enabled), now, list_id, user_id),
            )
        return True

    def delete_smart_list(self, user_id, list_id):
        row = self.connection.execute(
            "SELECT is_system FROM smart_lists WHERE id = %s AND user_id = %s", (list_id, user_id)
        ).fetchone()
        if row is None:
            return False
        if row["is_system"]:
            raise ValueError("system smart lists cannot be deleted")
        with self.connection.transaction():
            self.connection.execute("DELETE FROM smart_lists WHERE id = %s AND user_id = %s", (list_id, user_id))
        return True

    def save_search(self, user_id, name, purpose, config):
        normalized = normalize_search_config(config)
        with self.connection.transaction():
            cursor = self.connection.execute(
                """INSERT INTO searches (user_id, name, purpose, config_json)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT(user_id, name) DO UPDATE SET
                       purpose = excluded.purpose,
                       config_json = excluded.config_json
                   RETURNING id""",
                (user_id, name, purpose, Jsonb(normalized)),
            )
            return cursor.fetchone()["id"]

    def get_search(self, search_id):
        row = self.connection.execute(
            "SELECT * FROM searches WHERE id = %s", (search_id,)
        ).fetchone()
        if row is None:
            return None
        result = to_dict(row)
        result["config"] = result.pop("config_json")
        return result

    def get_search_by_name(self, user_id, name):
        row = self.connection.execute(
            "SELECT id FROM searches WHERE user_id = %s AND name = %s", (user_id, name)
        ).fetchone()
        return self.get_search(row["id"]) if row else None

    def list_searches(self, user_id, active=None):
        if active is None:
            rows = self.connection.execute(
                "SELECT * FROM searches WHERE user_id = %s", (user_id,)
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM searches WHERE user_id = %s AND active = %s", (user_id, bool(active))
            ).fetchall()
        results = []
        for row in rows:
            item = to_dict(row)
            item["config"] = item.pop("config_json")
            results.append(item)
        return results

    def start_run(self, search_id):
        search = self.get_search(search_id)
        now = datetime.now(timezone.utc)
        with self.connection.transaction():
            cursor = self.connection.execute(
                """INSERT INTO runs (search_id, config_json, started_at, status)
                   VALUES (%s, %s, %s, 'running')
                   RETURNING id""",
                (search_id, Jsonb(search["config"]), now),
            )
            return cursor.fetchone()["id"]

    def get_run(self, run_id):
        row = self.connection.execute(
            "SELECT * FROM runs WHERE id = %s", (run_id,)
        ).fetchone()
        if row is None:
            return None
        result = to_dict(row)
        result["config"] = result.pop("config_json")
        return result

    def get_runs_with_sources(self, search_id, limit=20):
        rows = self.connection.execute(
            """SELECT r.id, r.started_at, r.completed_at, r.status,
                      json_agg(
                          json_build_object('source', sr.source, 'status', sr.status, 'count', sr.listing_count)
                          ORDER BY sr.id
                      ) FILTER (WHERE sr.id IS NOT NULL) AS sources
               FROM runs r
               LEFT JOIN source_runs sr ON sr.run_id = r.id
               WHERE r.search_id = %s
               GROUP BY r.id
               ORDER BY r.id DESC
               LIMIT %s""",
            (search_id, limit),
        ).fetchall()
        result = []
        for row in rows:
            d = to_dict(row)
            if d["sources"] is None:
                d["sources"] = []
            result.append(d)
        return result

    def record_source_result(self, run_id, source, status, listing_count, error=None):
        with self.connection.transaction():
            self.connection.execute(
                """INSERT INTO source_runs (run_id, source, status, listing_count, error)
                   VALUES (%s, %s, %s, %s, %s)""",
                (run_id, source, status, listing_count, error),
            )

    def save_listing(self, run_id, listing):
        missing = [key for key in REQUIRED_LISTING_FIELDS if listing.get(key) in (None, "")]
        if missing:
            raise ValueError(f"listing missing required fields: {', '.join(missing)}")
        previous = self.connection.execute(
            """SELECT lv.payload_json FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.source = %s AND l.source_listing_id = %s
               ORDER BY lv.id DESC LIMIT 1""",
            (listing["source"], str(listing["source_listing_id"])),
        ).fetchone()
        if previous:
            previous_payload = previous["payload_json"]
            images = []
            for payload in (previous_payload, listing):
                values = list(payload.get("images") or [])
                values.extend(payload.get(key) for key in ("image_url_1", "image_url_2"))
                for image in values:
                    if image not in (None, "") and image not in images:
                        images.append(image)
            if images:
                listing = {**listing, "images": images, "image_url_1": images[0], "image_url_2": images[1] if len(images) > 1 else None}
        observed_at = datetime.now(timezone.utc)
        content_hash = _normalized_listing_fingerprint(listing)
        with self.connection.transaction():
            cursor = self.connection.execute(
                """INSERT INTO listings
                   (source, source_listing_id, url, transaction_type, first_seen_at, last_seen_at)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT(source, source_listing_id) DO UPDATE SET
                       url = excluded.url,
                       transaction_type = excluded.transaction_type,
                       last_seen_at = excluded.last_seen_at
                   RETURNING id""",
                (listing["source"], str(listing["source_listing_id"]), listing["url"],
                 listing["transaction_type"], observed_at, observed_at),
            )
            listing_id = cursor.fetchone()["id"]
            self.connection.execute(
                """INSERT INTO listing_versions
                   (listing_id, run_id, observed_at, content_hash, payload_json)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (listing_id, content_hash) DO NOTHING""",
                (listing_id, run_id, observed_at, content_hash, Jsonb(listing)),
            )
        return listing_id

    def finish_run(self, run_id, status):
        completed_at = datetime.now(timezone.utc)
        with self.connection.transaction():
            self.connection.execute(
                "UPDATE runs SET status = %s, completed_at = %s WHERE id = %s",
                (status, completed_at, run_id),
            )

    def get_listing(self, source, source_listing_id):
        row = self.connection.execute(
            """SELECT lv.payload_json FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.source = %s AND l.source_listing_id = %s
               ORDER BY lv.id DESC LIMIT 1""",
            (source, str(source_listing_id)),
        ).fetchone()
        return row["payload_json"] if row else None

    def latest_listings(self, transaction_type):
        rows = self.connection.execute(
            """SELECT lv.payload_json, l.first_seen_at, l.last_seen_at, lv.observed_at AS last_updated_at,
                      EXISTS(
                          SELECT 1 FROM listing_versions lv_old
                          WHERE lv_old.listing_id = l.id
                          AND lv_old.id < lv.id
                          AND (lv_old.payload_json->>'price')::NUMERIC >
                              (lv.payload_json->>'price')::NUMERIC
                      ) AS price_reduced
               FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.transaction_type = %s
               AND lv.id = (
                   SELECT MAX(lv2.id) FROM listing_versions lv2 WHERE lv2.listing_id = lv.listing_id
               )""",
            (transaction_type,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row["payload_json"])
            item["_first_seen_at"] = row["first_seen_at"].isoformat() if hasattr(row["first_seen_at"], "isoformat") else row["first_seen_at"]
            item["_last_seen_at"] = row["last_seen_at"].isoformat() if hasattr(row["last_seen_at"], "isoformat") else row["last_seen_at"]
            item["_last_updated_at"] = row["last_updated_at"].isoformat() if hasattr(row["last_updated_at"], "isoformat") else row["last_updated_at"]
            item["_price_reduced"] = bool(row["price_reduced"])
            result.append(item)
        return result

    def listings_for_run(self, run_id):
        rows = self.connection.execute(
            """SELECT lv.payload_json, l.first_seen_at
               FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE lv.run_id = %s
               ORDER BY lv.id""",
            (run_id,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row["payload_json"])
            item["_first_seen_at"] = row["first_seen_at"].isoformat() if hasattr(row["first_seen_at"], "isoformat") else row["first_seen_at"]
            result.append(item)
        return result

    def listing_history(self, source, source_listing_id):
        rows = self.connection.execute(
            """SELECT lv.observed_at, lv.payload_json, lv.id
               FROM listing_versions lv INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.source = %s AND l.source_listing_id = %s ORDER BY lv.id""",
            (source, str(source_listing_id)),
        ).fetchall()
        return [
            {
                "observed_at": row["observed_at"].isoformat() if hasattr(row["observed_at"], "isoformat") else row["observed_at"],
                "payload": row["payload_json"],
            }
            for row in rows
        ]

    def delete_listing(self, source, source_listing_id):
        with self.connection.transaction():
            row = self.connection.execute(
                "SELECT id FROM listings WHERE source = %s AND source_listing_id = %s",
                (source, str(source_listing_id)),
            ).fetchone()
            if row:
                lid = row["id"]
                self.connection.execute(
                    "DELETE FROM listing_versions WHERE listing_id = %s", (lid,)
                )
                self.connection.execute("DELETE FROM listings WHERE id = %s", (lid,))

    def merge_listing_payload(self, source, source_listing_id, payload):
        source_listing_id = str(source_listing_id)
        payload_str = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        content_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        with self.connection.transaction():
            row = self.connection.execute(
                """SELECT l.id, lv.run_id FROM listings l
                   INNER JOIN listing_versions lv ON lv.listing_id = l.id
                   WHERE l.source = %s AND l.source_listing_id = %s
                   ORDER BY lv.id DESC LIMIT 1""",
                (source, source_listing_id),
            ).fetchone()
            if not row:
                return
            self.connection.execute(
                """INSERT INTO listing_versions
                   (listing_id, run_id, observed_at, content_hash, payload_json)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (listing_id, content_hash) DO NOTHING""",
                (row["id"], row["run_id"], datetime.now(timezone.utc), content_hash, Jsonb(payload)),
            )

    def update_translation(self, source, source_listing_id, description_english, description_language):
        source_listing_id = str(source_listing_id)
        with self.connection.transaction():
            row = self.connection.execute(
                """SELECT lv.id, lv.payload_json FROM listing_versions lv
                   INNER JOIN listings l ON l.id = lv.listing_id
                   WHERE l.source = %s AND l.source_listing_id = %s
                   ORDER BY lv.id DESC LIMIT 1""",
                (source, source_listing_id),
            ).fetchone()
            if not row:
                return
            payload = dict(row["payload_json"])
            payload["description_english"] = description_english
            payload["description_language"] = description_language
            self.connection.execute(
                "UPDATE listing_versions SET payload_json = %s WHERE id = %s",
                (Jsonb(payload), row["id"]),
            )

    def get_lists(self, user_id):
        rows = self.connection.execute(
            """SELECT pl.id, pl.name, pl.created_at, COUNT(li.id) as item_count
               FROM property_lists pl
               LEFT JOIN list_items li ON li.list_id = pl.id
               WHERE pl.user_id = %s
               GROUP BY pl.id ORDER BY pl.created_at""",
            (user_id,),
        ).fetchall()
        return [to_dict(r) for r in rows]

    def create_list(self, user_id, name):
        with self.connection.transaction():
            cursor = self.connection.execute(
                """INSERT INTO property_lists (user_id, name, created_at) VALUES (%s, %s, %s)
                   ON CONFLICT (user_id, name) DO UPDATE SET created_at = property_lists.created_at
                   RETURNING id""",
                (user_id, name.strip(), datetime.now(timezone.utc)),
            )
            return cursor.fetchone()["id"]

    def delete_list(self, user_id, list_id):
        with self.connection.transaction():
            self.connection.execute(
                "DELETE FROM property_lists WHERE id = %s AND user_id = %s", (list_id, user_id)
            )

    def add_to_list(self, user_id, list_id, source, source_listing_id):
        row = self.connection.execute(
            "SELECT id FROM property_lists WHERE id = %s AND user_id = %s", (list_id, user_id)
        ).fetchone()
        if not row:
            raise ValueError("list not found")
        with self.connection.transaction():
            self.connection.execute(
                """INSERT INTO list_items (list_id, source, source_listing_id, added_at)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (list_id, source, source_listing_id) DO NOTHING""",
                (list_id, source, str(source_listing_id), datetime.now(timezone.utc)),
            )

    def remove_from_list(self, user_id, list_id, source, source_listing_id):
        row = self.connection.execute(
            "SELECT id FROM property_lists WHERE id = %s AND user_id = %s", (list_id, user_id)
        ).fetchone()
        if not row:
            raise ValueError("list not found")
        with self.connection.transaction():
            self.connection.execute(
                "DELETE FROM list_items WHERE list_id = %s AND source = %s AND source_listing_id = %s",
                (list_id, source, str(source_listing_id)),
            )

    def get_list_items(self, user_id, list_id):
        row = self.connection.execute(
            "SELECT id FROM property_lists WHERE id = %s AND user_id = %s", (list_id, user_id)
        ).fetchone()
        if not row:
            return []
        rows = self.connection.execute(
            """SELECT lv.payload_json
               FROM list_items li
               INNER JOIN listings l ON l.source = li.source AND l.source_listing_id = li.source_listing_id
               INNER JOIN listing_versions lv ON lv.listing_id = l.id
               WHERE li.list_id = %s
               AND lv.id = (
                   SELECT MAX(lv2.id) FROM listing_versions lv2 WHERE lv2.listing_id = lv.listing_id
               )
               ORDER BY li.added_at""",
            (list_id,),
        ).fetchall()
        return [dict(row["payload_json"]) for row in rows]

    def get_property_list_ids(self, user_id, source, source_listing_id):
        rows = self.connection.execute(
            """SELECT li.list_id FROM list_items li
               INNER JOIN property_lists pl ON pl.id = li.list_id
               WHERE li.source = %s AND li.source_listing_id = %s AND pl.user_id = %s""",
            (source, str(source_listing_id), user_id),
        ).fetchall()
        return {row["list_id"] for row in rows}

    def save_note(self, user_id, source, source_listing_id, note):
        updated_at = datetime.now(timezone.utc)
        with self.connection.transaction():
            self.connection.execute(
                """INSERT INTO property_notes (user_id, source, source_listing_id, note, updated_at)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT(user_id, source, source_listing_id) DO UPDATE SET
                       note = excluded.note,
                       updated_at = excluded.updated_at""",
                (user_id, source, str(source_listing_id), note, updated_at),
            )

    def get_note(self, user_id, source, source_listing_id):
        row = self.connection.execute(
            "SELECT note FROM property_notes WHERE user_id = %s AND source = %s AND source_listing_id = %s",
            (user_id, source, str(source_listing_id)),
        ).fetchone()
        return row["note"] if row else ""

    def get_all_notes(self, user_id):
        rows = self.connection.execute(
            "SELECT source, source_listing_id, note FROM property_notes WHERE user_id = %s",
            (user_id,),
        ).fetchall()
        return {(r["source"], r["source_listing_id"]): r["note"] for r in rows}

    def get_workflow(self, user_id, source, source_listing_id):
        row = self.connection.execute(
            "SELECT * FROM listing_workflow WHERE user_id = %s AND source = %s AND source_listing_id = %s",
            (user_id, source, str(source_listing_id)),
        ).fetchone()
        if row:
            return to_dict(row)
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
            "rating": None,
        }

    def save_workflow(self, user_id, source, source_listing_id, data):
        allowed = ("status", "contact_date", "next_follow_up_date", "agent_name", "agent_phone", "agent_email", "offer_amount", "rejection_reason", "rating")
        values = {key: data.get(key) for key in allowed}
        values["status"] = values["status"] or "New"
        if values["status"] not in ("New", "Interested", "Contacted", "Visit planned", "Offer", "Rejected", "On hold"):
            raise ValueError("invalid workflow status")
        previous = self.connection.execute(
            "SELECT status FROM listing_workflow WHERE user_id = %s AND source = %s AND source_listing_id = %s",
            (user_id, source, str(source_listing_id)),
        ).fetchone()
        updated_at = datetime.now(timezone.utc)
        with self.connection.transaction():
            self.connection.execute(
                """INSERT INTO listing_workflow (user_id, source, source_listing_id, status, contact_date, next_follow_up_date, agent_name, agent_phone, agent_email, offer_amount, rejection_reason, rating, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT(user_id, source, source_listing_id) DO UPDATE SET status=excluded.status, contact_date=excluded.contact_date, next_follow_up_date=excluded.next_follow_up_date, agent_name=excluded.agent_name, agent_phone=excluded.agent_phone, agent_email=excluded.agent_email, offer_amount=excluded.offer_amount, rejection_reason=excluded.rejection_reason, rating=excluded.rating, updated_at=excluded.updated_at""",
                (user_id, source, str(source_listing_id), values["status"], values["contact_date"], values["next_follow_up_date"], values["agent_name"], values["agent_phone"], values["agent_email"], values["offer_amount"], values["rejection_reason"] or "", values.get("rating"), updated_at),
            )
            if (previous is None and values["status"] != "New") or (previous is not None and previous["status"] != values["status"]):
                self.connection.execute(
                    "INSERT INTO listing_interactions (user_id, source, source_listing_id, kind, note, occurred_at, next_follow_up_date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (user_id, source, str(source_listing_id), "status", "Status changed to " + values["status"] + (": " + values["rejection_reason"] if values["status"] == "Rejected" and values["rejection_reason"] else ""), updated_at, values["next_follow_up_date"]),
                )
        return self.get_workflow(user_id, source, source_listing_id)

    def add_interaction(self, user_id, source, source_listing_id, kind, note="", occurred_at=None, next_follow_up_date=None):
        if kind not in ("call", "email", "message", "visit", "status", "other"):
            raise ValueError("invalid interaction kind")
        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)
        elif isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at)
        with self.connection.transaction():
            cursor = self.connection.execute(
                "INSERT INTO listing_interactions (user_id, source, source_listing_id, kind, note, occurred_at, next_follow_up_date) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (user_id, source, str(source_listing_id), kind, (note or "").strip(), occurred_at, next_follow_up_date),
            )
            new_id = cursor.fetchone()["id"]
        row = self.connection.execute(
            "SELECT * FROM listing_interactions WHERE id = %s", (new_id,)
        ).fetchone()
        return to_dict(row)

    def get_interactions(self, user_id, source, source_listing_id):
        rows = self.connection.execute(
            "SELECT * FROM listing_interactions WHERE user_id = %s AND source = %s AND source_listing_id = %s ORDER BY occurred_at DESC, id DESC",
            (user_id, source, str(source_listing_id)),
        ).fetchall()
        return [to_dict(row) for row in rows]

    def version_count(self, source, source_listing_id):
        row = self.connection.execute(
            """SELECT COUNT(*) as cnt FROM listing_versions lv
               INNER JOIN listings l ON l.id = lv.listing_id
               WHERE l.source = %s AND l.source_listing_id = %s""",
            (source, str(source_listing_id)),
        ).fetchone()
        return row["cnt"]

    def add_alert(self, user_id, source, source_listing_id, kind, message, url):
        with self.connection.transaction():
            self.connection.execute(
                """INSERT INTO alerts (user_id, source, source_listing_id, kind, message, url, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (user_id, source, source_listing_id, kind) DO NOTHING""",
                (user_id, source, str(source_listing_id), kind, message, url, datetime.now(timezone.utc)),
            )

    def get_alerts(self, user_id):
        rows = self.connection.execute(
            """SELECT a.*,
                      lv.payload_json
               FROM alerts a
               LEFT JOIN listings l ON l.source = a.source AND l.source_listing_id = a.source_listing_id
               LEFT JOIN listing_versions lv ON lv.listing_id = l.id
                 AND lv.id = (SELECT MAX(id) FROM listing_versions WHERE listing_id = l.id)
               WHERE a.user_id = %s
               ORDER BY a.id DESC LIMIT 100""",
            (user_id,),
        ).fetchall()
        result = []
        for row in rows:
            alert = to_dict(row)
            payload = alert.pop("payload_json", None)
            if payload:
                alert["listing_price"] = payload.get("price")
                alert["listing_postcode"] = payload.get("postcode")
                street = payload.get("street") or payload.get("address") or ""
                city = payload.get("city") or ""
                alert["listing_address"] = f"{street}, {city}".strip(", ") or None
                alert["listing_property_type"] = payload.get("property_type")
            result.append(alert)
        return result

    def mark_alert_read(self, user_id, alert_id):
        with self.connection.transaction():
            self.connection.execute(
                "UPDATE alerts SET read_at = %s WHERE id = %s AND user_id = %s",
                (datetime.now(timezone.utc), alert_id, user_id),
            )

    def get_alerts_since(self, user_id):
        row = self.connection.execute(
            "SELECT alerts_since FROM users WHERE id = %s", (user_id,)
        ).fetchone()
        if row and row["alerts_since"]:
            value = row["alerts_since"]
            if isinstance(value, str):
                return datetime.fromisoformat(value).astimezone(timezone.utc)
            return value.astimezone(timezone.utc)
        return None

    def clear_alerts(self, user_id):
        now = datetime.now(timezone.utc)
        with self.connection.transaction():
            self.connection.execute(
                "DELETE FROM alerts WHERE user_id = %s", (user_id,)
            )
            self.connection.execute(
                "UPDATE users SET alerts_since = %s WHERE id = %s", (now, user_id)
            )

    def close(self):
        self.connection.close()
