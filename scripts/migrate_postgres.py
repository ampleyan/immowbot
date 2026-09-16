#!/usr/bin/env python3
"""Apply PostgreSQL schema migrations to initialize the immotool database."""

import sys
from pathlib import Path

# Allow running from the repo root
sys.path.insert(0, str(Path(__file__).parents[1]))

from src.buyer.database import load_database_settings
from src.buyer.postgres_migrations import apply_migrations


def main():
    try:
        settings = load_database_settings()
    except ValueError as exc:
        print(f"database configuration error: {exc}", file=sys.stderr)
        return 1

    try:
        applied = apply_migrations(settings.dsn, owner_role=None)
    except Exception as exc:
        print(f"migration failed: {exc}", file=sys.stderr)
        return 1

    if applied:
        print("Applied:", ", ".join(applied))
    else:
        print("Schema up to date")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
