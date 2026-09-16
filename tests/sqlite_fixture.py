"""Creates a complete SQLite fixture for importer tests."""

import json
import sqlite3
from pathlib import Path


CREATE_STATEMENTS = [
    """CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        alerts_since TEXT
    )""",
    """CREATE TABLE property_lists (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL DEFAULT 1,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, name)
    )""",
    """CREATE TABLE list_items (
        id INTEGER PRIMARY KEY,
        list_id INTEGER NOT NULL,
        source TEXT NOT NULL,
        source_listing_id TEXT NOT NULL,
        added_at TEXT NOT NULL,
        UNIQUE(list_id, source, source_listing_id)
    )""",
    """CREATE TABLE property_notes (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL DEFAULT 1,
        source TEXT NOT NULL,
        source_listing_id TEXT NOT NULL,
        note TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, source, source_listing_id)
    )""",
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
        rating INTEGER,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (user_id, source, source_listing_id)
    )""",
    """CREATE TABLE listing_interactions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL DEFAULT 1,
        source TEXT NOT NULL,
        source_listing_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        occurred_at TEXT NOT NULL,
        next_follow_up_date TEXT
    )""",
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
    """CREATE TABLE searches (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL DEFAULT 1,
        name TEXT NOT NULL,
        purpose TEXT NOT NULL,
        config_json TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(user_id, name)
    )""",
    """CREATE TABLE runs (
        id INTEGER PRIMARY KEY,
        search_id INTEGER NOT NULL,
        config_json TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        status TEXT NOT NULL
    )""",
    """CREATE TABLE source_runs (
        id INTEGER PRIMARY KEY,
        run_id INTEGER NOT NULL,
        source TEXT NOT NULL,
        status TEXT NOT NULL,
        listing_count INTEGER NOT NULL DEFAULT 0,
        error TEXT
    )""",
    """CREATE TABLE listings (
        id INTEGER PRIMARY KEY,
        source TEXT NOT NULL,
        source_listing_id TEXT NOT NULL,
        url TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        UNIQUE(source, source_listing_id)
    )""",
    """CREATE TABLE listing_versions (
        id INTEGER PRIMARY KEY,
        listing_id INTEGER NOT NULL,
        run_id INTEGER NOT NULL,
        observed_at TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        UNIQUE(listing_id, content_hash)
    )""",
]


def create_complete_sqlite_fixture(path):
    path = Path(path)
    conn = sqlite3.connect(str(path))

    for stmt in CREATE_STATEMENTS:
        conn.execute(stmt)

    # 2 users: admin + regular
    conn.execute(
        "INSERT INTO users (id, username, password_hash, is_admin, created_at, alerts_since)"
        " VALUES (1, 'admin', 'hash_admin', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO users (id, username, password_hash, is_admin, created_at, alerts_since)"
        " VALUES (2, 'buyer', 'hash_buyer', 0, '2024-01-15T10:00:00Z', NULL)"
    )

    # 1 property_list
    conn.execute(
        "INSERT INTO property_lists (id, user_id, name, created_at)"
        " VALUES (1, 1, 'Favourites', '2024-02-01T00:00:00Z')"
    )

    # 1 smart_list
    conn.execute(
        "INSERT INTO smart_lists (id, user_id, name, rule_json, is_system, enabled, created_at, updated_at)"
        " VALUES (1, 1, 'Under 200k', ?, 0, 1, '2024-02-01T00:00:00Z', '2024-02-01T00:00:00Z')",
        (json.dumps({"max_price": 200000}),),
    )

    # 1 search
    conn.execute(
        "INSERT INTO searches (id, user_id, name, purpose, config_json, active)"
        " VALUES (1, 1, 'Antwerp homes', 'home', ?, 1)",
        (json.dumps({"max_price": 250000, "postal_codes": ["2000", "2060"]}),),
    )

    # 2 listings (non-default IDs preserved but not specified for listings)
    conn.execute(
        "INSERT INTO listings (id, source, source_listing_id, url, transaction_type,"
        " first_seen_at, last_seen_at)"
        " VALUES (1, 'immoweb', 'listing-001',"
        " 'https://immoweb.be/en/classified/1', 'sale',"
        " '2024-03-01T08:00:00Z', '2024-04-01T08:00:00Z')"
    )
    conn.execute(
        "INSERT INTO listings (id, source, source_listing_id, url, transaction_type,"
        " first_seen_at, last_seen_at)"
        " VALUES (2, 'immoweb', 'listing-002',"
        " 'https://immoweb.be/en/classified/2', 'sale',"
        " '2024-03-02T09:00:00Z', '2024-04-02T09:00:00Z')"
    )

    # 1 run
    conn.execute(
        "INSERT INTO runs (id, search_id, config_json, started_at, completed_at, status)"
        " VALUES (1, 1, ?, '2024-04-01T08:00:00Z', '2024-04-01T08:30:00Z', 'completed')",
        (json.dumps({"pages": 5}),),
    )

    # 1 source_run
    conn.execute(
        "INSERT INTO source_runs (id, run_id, source, status, listing_count, error)"
        " VALUES (1, 1, 'immoweb', 'completed', 2, NULL)"
    )

    # listing_versions with IDs 701 and 702 (non-default to verify ID preservation)
    conn.execute(
        "INSERT INTO listing_versions"
        " (id, listing_id, run_id, observed_at, content_hash, payload_json)"
        " VALUES (701, 1, 1, '2024-04-01T08:15:00Z', 'hash-a1', ?)",
        (json.dumps({"price": 300000, "surface": 120, "bedrooms": 3}),),
    )
    conn.execute(
        "INSERT INTO listing_versions"
        " (id, listing_id, run_id, observed_at, content_hash, payload_json)"
        " VALUES (702, 2, 1, '2024-04-01T08:20:00Z', 'hash-b2', ?)",
        (json.dumps({"price": 185000, "surface": 85, "bedrooms": 2}),),
    )

    # 1 list_item
    conn.execute(
        "INSERT INTO list_items (id, list_id, source, source_listing_id, added_at)"
        " VALUES (1, 1, 'immoweb', 'listing-001', '2024-04-02T10:00:00Z')"
    )

    # 1 property_note
    conn.execute(
        "INSERT INTO property_notes (id, user_id, source, source_listing_id, note, updated_at)"
        " VALUES (1, 1, 'immoweb', 'listing-001', 'Great location', '2024-04-03T11:00:00Z')"
    )

    # 1 listing_workflow row (composite PK, no id)
    conn.execute(
        "INSERT INTO listing_workflow"
        " (user_id, source, source_listing_id, status, contact_date,"
        "  next_follow_up_date, agent_name, agent_phone, agent_email,"
        "  offer_amount, rejection_reason, rating, updated_at)"
        " VALUES (1, 'immoweb', 'listing-001', 'Contacted', '2024-04-10',"
        "  '2024-04-17', 'Jan Janssen', '+32 123 456 789', 'jan@agency.be',"
        "  290000.0, '', 4, '2024-04-10T14:00:00Z')"
    )

    # 1 listing_interaction
    conn.execute(
        "INSERT INTO listing_interactions"
        " (id, user_id, source, source_listing_id, kind, note, occurred_at, next_follow_up_date)"
        " VALUES (1, 1, 'immoweb', 'listing-001', 'visit', 'Visited the property', '2024-04-05T14:00:00Z', '2024-04-12')"
    )

    # 1 alert
    conn.execute(
        "INSERT INTO alerts"
        " (id, user_id, source, source_listing_id, kind, message, url, created_at, read_at)"
        " VALUES (1, 1, 'immoweb', 'listing-001', 'price_drop',"
        " 'Price dropped from 310000 to 300000',"
        " 'https://immoweb.be/en/classified/1', '2024-04-06T09:00:00Z', NULL)"
    )

    conn.commit()
    conn.close()
    return path
