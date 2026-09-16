"""One-shot SQLite-to-PostgreSQL importer with immutable rollback archives."""

import hashlib
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb


ADVISORY_LOCK_KEY = 1234567890

DOMAIN_TABLES = [
    "users",
    "property_lists",
    "list_items",
    "property_notes",
    "listing_workflow",
    "listing_interactions",
    "alerts",
    "smart_lists",
    "searches",
    "runs",
    "source_runs",
    "listings",
    "listing_versions",
]

# Insertion order respects foreign key dependencies
INSERT_ORDER = [
    "users",
    "property_lists",
    "smart_lists",
    "searches",
    "listings",
    "runs",
    "list_items",
    "property_notes",
    "listing_workflow",
    "listing_interactions",
    "alerts",
    "source_runs",
    "listing_versions",
]

JSONB_COLUMNS = frozenset({"payload_json", "rule_json", "config_json"})
BOOLEAN_COLUMNS = frozenset({"is_admin", "is_system", "enabled", "active"})

# Tables that have an 'id' identity column (listing_workflow has composite PK, no id column)
IDENTITY_TABLES = [
    "users",
    "property_lists",
    "list_items",
    "property_notes",
    "listing_interactions",
    "alerts",
    "smart_lists",
    "searches",
    "runs",
    "source_runs",
    "listings",
    "listing_versions",
]

ARCHIVE_PATTERN = re.compile(
    r"^immowbot-archive-(\d{8}T\d{6}Z)-[0-9a-f]{8}\.sqlite3$"
)


class ImportReport:
    def __init__(self, table_counts, archive_basename):
        self.table_counts = table_counts
        self.archive_basename = archive_basename


class SQLiteSource:
    def __init__(self, conn, path):
        self.conn = conn
        self.path = path


def validate_sqlite_source(sqlite_path):
    path = Path(sqlite_path)
    if not path.is_absolute():
        raise ValueError(f"sqlite_path must be absolute: {path}")
    if path.is_symlink():
        raise ValueError(f"sqlite_path must not be a symlink: {path}")
    if not path.is_file():
        raise ValueError(f"sqlite_path must be a regular file: {path}")

    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if result[0] != "ok":
            conn.close()
            raise ValueError(f"SQLite integrity check failed: {result[0]}")

        fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_violations:
            conn.close()
            raise ValueError(
                f"SQLite foreign key violations found: {len(fk_violations)} rows"
            )

        actual_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        missing = frozenset(DOMAIN_TABLES) - actual_tables
        if missing:
            conn.close()
            raise ValueError(
                f"SQLite source missing expected tables: {sorted(missing)}"
            )
    except Exception:
        conn.close()
        raise

    return SQLiteSource(conn, path)


def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def publish_rollback_archive(source, archive_dir):
    archive_dir = Path(archive_dir)
    if not archive_dir.is_absolute():
        raise ValueError(f"archive_dir must be absolute: {archive_dir}")
    if archive_dir.is_symlink():
        raise ValueError(f"archive_dir must not be a symlink: {archive_dir}")
    if not archive_dir.is_dir():
        raise ValueError(
            f"archive_dir must be an existing directory: {archive_dir}"
        )

    source_path = source.path
    sha256 = compute_sha256(source_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_name = f"immowbot-archive-{timestamp}-{sha256[:8]}.sqlite3"

    # Refuse to overwrite: check for any existing archive with same sha256 prefix
    existing = list(archive_dir.glob(f"immowbot-archive-*-{sha256[:8]}.sqlite3"))
    if existing:
        raise ValueError(
            f"Archive already exists for this source file: {existing[0].name}"
        )

    staging_path = archive_dir / (archive_name + ".tmp")
    final_path = archive_dir / archive_name

    shutil.copy2(source_path, staging_path)
    with open(staging_path, "rb") as f:
        os.fsync(f.fileno())
    staging_path.rename(final_path)
    os.chmod(final_path, 0o444)

    table_counts = {}
    for table in DOMAIN_TABLES:
        try:
            count = source.conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            table_counts[table] = count
        except sqlite3.Error:
            table_counts[table] = 0

    manifest = {
        "sha256": sha256,
        "archive_basename": archive_name,
        "timestamp": timestamp,
        "table_counts": table_counts,
    }
    manifest_path = archive_dir / (archive_name + ".json")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    os.chmod(manifest_path, 0o444)

    return final_path


def acquire_import_lock(conn):
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (ADVISORY_LOCK_KEY,))


def require_empty_baseline(conn):
    for table in DOMAIN_TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if count > 0:
            raise ValueError(
                f"Target table '{table}' is not empty ({count} rows); "
                "import requires an empty baseline"
            )


def adapt_value(value, col_name):
    if value is None:
        return None
    if col_name in BOOLEAN_COLUMNS:
        return bool(value)
    if col_name in JSONB_COLUMNS:
        if isinstance(value, str):
            return Jsonb(json.loads(value))
        return Jsonb(value)
    return value


def insert_all_tables_with_explicit_ids(source, pg_conn):
    for table in INSERT_ORDER:
        cursor = source.conn.execute(f"SELECT * FROM {table} LIMIT 0")
        cols = [desc[0] for desc in cursor.description]

        rows = source.conn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            continue

        placeholders = ", ".join(["%s"] * len(cols))
        col_list = ", ".join(cols)
        stmt = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
            " ON CONFLICT DO NOTHING"
        )

        for row in rows:
            adapted = tuple(adapt_value(row[i], cols[i]) for i in range(len(cols)))
            pg_conn.execute(stmt, adapted)


def validate_counts(source, pg_conn):
    mismatches = []
    for table in DOMAIN_TABLES:
        sqlite_count = source.conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        pg_count = pg_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if sqlite_count != pg_count:
            mismatches.append(
                f"{table}: sqlite={sqlite_count}, postgres={pg_count}"
            )
    if mismatches:
        raise ValueError(
            f"Row count mismatches after import: {'; '.join(mismatches)}"
        )


def validate_foreign_keys(pg_conn):
    fk_query = """
        SELECT
            tc.table_name AS child_table,
            kcu.column_name AS child_col,
            ccu.table_name AS parent_table,
            ccu.column_name AS parent_col
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
    """
    fks = pg_conn.execute(fk_query).fetchall()

    violations = []
    for child_table, child_col, parent_table, parent_col in fks:
        check_sql = f"""
            SELECT COUNT(*)
            FROM {child_table} c
            WHERE c.{child_col} IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM {parent_table} p
                WHERE p.{parent_col} = c.{child_col}
              )
        """
        count = pg_conn.execute(check_sql).fetchone()[0]
        if count > 0:
            violations.append(
                f"{child_table}.{child_col} -> {parent_table}.{parent_col}: "
                f"{count} violations"
            )

    if violations:
        raise ValueError(
            f"Foreign key violations after import: {'; '.join(violations)}"
        )


def reset_identity_sequences(pg_conn):
    for table in IDENTITY_TABLES:
        pg_conn.execute(
            f"SELECT setval("
            f"pg_get_serial_sequence('{table}', 'id'), "
            f"GREATEST(MAX(id), 1)) FROM {table}"
        )


def import_sqlite_to_postgres(sqlite_path, postgres_dsn, archive_dir):
    source = validate_sqlite_source(sqlite_path)
    archive = publish_rollback_archive(source, archive_dir)

    table_counts = {}
    for table in DOMAIN_TABLES:
        table_counts[table] = source.conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

    with psycopg.connect(postgres_dsn) as target:
        with target.transaction():
            acquire_import_lock(target)
            require_empty_baseline(target)
            insert_all_tables_with_explicit_ids(source, target)
            validate_counts(source, target)
            validate_foreign_keys(target)
            reset_identity_sequences(target)

    source.conn.close()

    return ImportReport(
        table_counts=table_counts,
        archive_basename=archive.name,
    )


def prune_expired_archives(archive_dir, now):
    archive_dir = Path(archive_dir)
    if not archive_dir.is_absolute():
        raise ValueError(f"archive_dir must be absolute: {archive_dir}")
    if archive_dir.is_symlink():
        raise ValueError(f"archive_dir must not be a symlink: {archive_dir}")
    if not archive_dir.is_dir():
        raise ValueError(
            f"archive_dir must be an existing directory: {archive_dir}"
        )

    cutoff = now - timedelta(days=30)
    deleted = []

    for path in sorted(archive_dir.iterdir()):
        if path.is_symlink():
            continue
        if not path.is_file():
            continue

        match = ARCHIVE_PATTERN.match(path.name)
        if not match:
            continue

        timestamp_str = match.group(1)
        archive_time = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )

        if archive_time < cutoff:
            path.unlink()
            deleted.append(path)

            manifest_path = path.parent / (path.name + ".json")
            if manifest_path.exists() and not manifest_path.is_symlink():
                manifest_path.unlink()
                deleted.append(manifest_path)

    return deleted
