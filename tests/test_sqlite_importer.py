"""Tests for the one-shot SQLite-to-PostgreSQL importer."""

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import psycopg

from tests.postgres_support import PostgresDatabaseTestCase, postgres_test_dsn
from tests.sqlite_fixture import create_complete_sqlite_fixture
from src.buyer.sqlite_importer import (
    import_sqlite_to_postgres,
    prune_expired_archives,
    validate_sqlite_source,
)


def fetch_ids(dsn, table):
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(f"SELECT id FROM {table} ORDER BY id").fetchall()
    return [row[0] for row in rows]


def fetch_payload(dsn, version_id):
    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            "SELECT payload_json FROM listing_versions WHERE id = %s", (version_id,)
        ).fetchone()
    return row[0] if row else None


def postgres_foreign_key_violations(dsn):
    fk_query = """
        SELECT tc.table_name, kcu.column_name,
               ccu.table_name AS ref_table, ccu.column_name AS ref_col
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
    """
    violations = []
    with psycopg.connect(dsn) as conn:
        fks = conn.execute(fk_query).fetchall()
        for child_table, child_col, parent_table, parent_col in fks:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {child_table} c"
                f" WHERE c.{child_col} IS NOT NULL"
                f" AND NOT EXISTS ("
                f"   SELECT 1 FROM {parent_table} p"
                f"   WHERE p.{parent_col} = c.{child_col}"
                f" )"
            ).fetchone()[0]
            if count > 0:
                violations.append(
                    f"{child_table}.{child_col} -> {parent_table}.{parent_col}"
                )
    return violations


class TestSQLiteImporter(PostgresDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.runtime_dsn = postgres_test_dsn()
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp_dir)
        self.archive_dir = self.tmp_path / "archives"
        self.archive_dir.mkdir()

    def tearDown(self):
        import shutil
        # Make archive files writable before cleanup
        for f in self.archive_dir.iterdir():
            try:
                os.chmod(f, 0o644)
            except OSError:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_import_preserves_ids_counts_and_relationships(self):
        source = create_complete_sqlite_fixture(self.tmp_path / "source.sqlite3")
        report = import_sqlite_to_postgres(source, self.runtime_dsn, self.archive_dir)

        self.assertEqual(report.table_counts["users"], 2)
        self.assertEqual(report.table_counts["listings"], 2)
        self.assertEqual(report.table_counts["listing_versions"], 2)

        version_ids = fetch_ids(self.runtime_dsn, "listing_versions")
        self.assertEqual(version_ids, [701, 702])

        payload = fetch_payload(self.runtime_dsn, 701)
        self.assertEqual(payload["price"], 300000)

        self.assertEqual(postgres_foreign_key_violations(self.runtime_dsn), [])

    def test_import_rejects_symlink_source(self):
        real_file = self.tmp_path / "real.sqlite3"
        create_complete_sqlite_fixture(real_file)

        symlink = self.tmp_path / "link.sqlite3"
        symlink.symlink_to(real_file)

        with self.assertRaises(ValueError) as ctx:
            import_sqlite_to_postgres(symlink, self.runtime_dsn, self.archive_dir)
        self.assertIn("symlink", str(ctx.exception).lower())

    def test_import_rejects_nonempty_target(self):
        source = create_complete_sqlite_fixture(self.tmp_path / "source.sqlite3")

        # Seed one row in Postgres to make target non-empty
        with psycopg.connect(self.runtime_dsn) as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at)"
                " VALUES ('pre-existing', 'hash', now())"
            )

        with self.assertRaises(ValueError) as ctx:
            import_sqlite_to_postgres(source, self.runtime_dsn, self.archive_dir)
        self.assertIn("not empty", str(ctx.exception))

    def test_import_rolls_back_target_rows_on_count_mismatch(self):
        source = create_complete_sqlite_fixture(self.tmp_path / "source.sqlite3")

        with patch(
            "src.buyer.sqlite_importer.validate_counts",
            side_effect=ValueError("injected count mismatch"),
        ):
            with self.assertRaises(ValueError):
                import_sqlite_to_postgres(source, self.runtime_dsn, self.archive_dir)

        # All domain tables must remain empty after rollback
        with psycopg.connect(self.runtime_dsn) as conn:
            for table in [
                "users", "listings", "listing_versions", "runs", "searches"
            ]:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                self.assertEqual(
                    count, 0, f"Table '{table}' has {count} rows after rollback"
                )

    def test_archive_is_read_only_and_not_overwritten(self):
        source = create_complete_sqlite_fixture(self.tmp_path / "source.sqlite3")
        report = import_sqlite_to_postgres(source, self.runtime_dsn, self.archive_dir)

        archive_path = self.archive_dir / report.archive_basename
        mode = oct(archive_path.stat().st_mode & 0o777)
        self.assertEqual(mode, oct(0o444), "Archive file must be read-only (0444)")

        # Reset the database for a clean second import attempt
        from tests.postgres_support import reset_postgres_database
        reset_postgres_database(self.runtime_dsn)

        with self.assertRaises(ValueError) as ctx:
            import_sqlite_to_postgres(source, self.runtime_dsn, self.archive_dir)
        self.assertIn("already exists", str(ctx.exception))

    def test_pruning_keeps_archives_younger_than_thirty_full_days(self):
        now = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)

        # Archive from 31 days ago — should be deleted
        old_ts = (now - timedelta(days=31)).strftime("%Y%m%dT%H%M%SZ")
        old_name = f"immowbot-archive-{old_ts}-aabbccdd.sqlite3"
        old_path = self.archive_dir / old_name
        old_path.write_text("old archive content")
        old_manifest = self.archive_dir / (old_name + ".json")
        old_manifest.write_text(json.dumps({"archive_basename": old_name}))

        # Archive from 29 days ago — should be kept
        recent_ts = (now - timedelta(days=29)).strftime("%Y%m%dT%H%M%SZ")
        recent_name = f"immowbot-archive-{recent_ts}-11223344.sqlite3"
        recent_path = self.archive_dir / recent_name
        recent_path.write_text("recent archive content")
        recent_manifest = self.archive_dir / (recent_name + ".json")
        recent_manifest.write_text(json.dumps({"archive_basename": recent_name}))

        deleted = prune_expired_archives(self.archive_dir, now)

        deleted_names = {p.name for p in deleted}
        self.assertIn(old_name, deleted_names)
        self.assertIn(old_name + ".json", deleted_names)
        self.assertNotIn(recent_name, deleted_names)
        self.assertNotIn(recent_name + ".json", deleted_names)

        self.assertFalse(old_path.exists())
        self.assertFalse(old_manifest.exists())
        self.assertTrue(recent_path.exists())
        self.assertTrue(recent_manifest.exists())

    def test_errors_and_reports_do_not_contain_dsn_password(self):
        source = create_complete_sqlite_fixture(self.tmp_path / "source.sqlite3")
        report = import_sqlite_to_postgres(source, self.runtime_dsn, self.archive_dir)

        # Extract the password from the test DSN
        import psycopg.conninfo
        params = psycopg.conninfo.conninfo_to_dict(self.runtime_dsn)
        password = params.get("password", "")

        archive_basename_str = str(report.archive_basename)
        table_counts_str = json.dumps(report.table_counts)

        if password:
            self.assertNotIn(password, archive_basename_str)
            self.assertNotIn(password, table_counts_str)

        # Also verify report has no dsn/connstring
        for field_val in [archive_basename_str, table_counts_str]:
            self.assertNotIn("postgresql://", field_val)
            self.assertNotIn("@127.0.0.1", field_val)
            self.assertNotIn("@localhost", field_val)


if __name__ == "__main__":
    unittest.main()
