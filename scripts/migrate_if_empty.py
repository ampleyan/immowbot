import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.buyer.postgres_migrations import apply_migrations
from src.buyer.sqlite_importer import import_sqlite_to_postgres


def database_has_application_data(connection):
    tables = connection.execute(
        """
        SELECT tablename
        FROM pg_catalog.pg_tables
        WHERE schemaname = 'public' AND tablename <> 'schema_migrations'
        """
    ).fetchall()
    for (table,) in tables:
        if connection.execute(
            sql.SQL("SELECT EXISTS (SELECT 1 FROM {} LIMIT 1)").format(
                sql.Identifier(table)
            )
        ).fetchone()[0]:
            return True
    return False


def main():
    dsn = os.environ["DATABASE_DSN"]
    sqlite_path = Path(os.environ.get("SQLITE_SOURCE_PATH", "/app/data/buyer.db"))
    archive_dir = Path(
        os.environ.get("SQLITE_ARCHIVE_DIR", "/app/data/sqlite-rollback-archives")
    )
    with psycopg.connect(dsn) as connection:
        if database_has_application_data(connection):
            print("Application data found; skipping bootstrap import")
            return 0

    applied = apply_migrations(dsn, owner_role=None)
    if applied:
        print("Applied:", ", ".join(applied))
    else:
        print("Schema up to date")

    if sqlite_path.is_file():
        archive_dir.mkdir(parents=True, exist_ok=True)
        report = import_sqlite_to_postgres(sqlite_path, dsn, archive_dir)
        print(f"Imported SQLite data — archive: {report.archive_basename}")
        return 0

    print(f"SQLite source not found; leaving the empty PostgreSQL database: {sqlite_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
