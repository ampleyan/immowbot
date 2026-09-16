#!/usr/bin/env python3
"""Import a SQLite database into PostgreSQL as a one-shot migration."""

import argparse
import os
import sys
from pathlib import Path

# Allow running from the repo root
sys.path.insert(0, str(Path(__file__).parents[1]))

from src.buyer.database import load_database_settings
from src.buyer.sqlite_importer import import_sqlite_to_postgres


def main():
    parser = argparse.ArgumentParser(
        description="Import a SQLite database into the Immowbot PostgreSQL database."
    )
    parser.add_argument(
        "--sqlite-path",
        required=True,
        help="Absolute path to the source SQLite file",
    )
    parser.add_argument(
        "--archive-dir",
        required=True,
        help="Absolute path to the directory for rollback archives",
    )
    args = parser.parse_args()

    try:
        settings = load_database_settings(os.environ)
    except ValueError as exc:
        print(f"database configuration error: {exc}", file=sys.stderr)
        return 1

    sqlite_path = Path(args.sqlite_path)
    archive_dir = Path(args.archive_dir)

    try:
        report = import_sqlite_to_postgres(sqlite_path, settings.dsn, archive_dir)
    except ValueError as exc:
        print(f"import failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"unexpected error: {exc}", file=sys.stderr)
        return 1

    print(f"import completed — archive: {report.archive_basename}")
    print("table counts:")
    for table, count in sorted(report.table_counts.items()):
        print(f"  {table}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
