#!/usr/bin/env python3
"""Create a clean PostgreSQL database and apply Immowbot's baseline schema."""
import argparse
import sys

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from src.buyer.postgres_migrations import apply_migrations


def main():
    parser = argparse.ArgumentParser(description="Create an empty Immowbot PostgreSQL database")
    parser.add_argument("--admin-dsn", required=True, help="maintenance/admin PostgreSQL DSN")
    parser.add_argument("--database", default="immotool")
    parser.add_argument("--owner-role", default="immotool_owner")
    parser.add_argument("--runtime-dsn", required=True, help="runtime PostgreSQL DSN")
    args = parser.parse_args()
    if args.database != "immotool" or args.owner_role != "immotool_owner":
        parser.error("only immotool owned by immotool_owner is supported")
    try:
        admin = conninfo_to_dict(args.admin_dsn)
        admin["dbname"] = "postgres"
        with psycopg.connect(make_conninfo(**admin), autocommit=True) as connection:
            exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (args.database,)).fetchone()
            if exists:
                raise RuntimeError("target database already exists; refusing to overwrite it")
            connection.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(args.database), sql.Identifier(args.owner_role)))
        apply_migrations(args.runtime_dsn, args.owner_role)
    except Exception as exc:
        print(f"database preparation failed: {exc}", file=sys.stderr)
        return 1
    print("empty immotool database created and baseline applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
