"""Shared test fixtures for PostgreSQL-backed property store tests."""
import os
import socket
import unittest

import psycopg

from src.buyer.postgres_migrations import apply_migrations

POSTGRES_TEST_DSN = os.environ.get(
    "POSTGRES_TEST_DSN",
    "postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test",
)


def validate_test_dsn(dsn):
    params = psycopg.conninfo.conninfo_to_dict(dsn)
    host = params.get("host", "127.0.0.1")
    dbname = params.get("dbname", "")
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError(f"Refusing to reset non-loopback DSN host: {host!r}")
    if not dbname.startswith("immowbot_test"):
        raise ValueError(f"Refusing to reset database not named immowbot_test*: {dbname!r}")


def postgres_test_dsn():
    if "POSTGRES_TEST_DSN" in os.environ:
        validate_test_dsn(POSTGRES_TEST_DSN)
        return POSTGRES_TEST_DSN
    try:
        params = psycopg.conninfo.conninfo_to_dict(POSTGRES_TEST_DSN)
        host = params.get("host", "127.0.0.1")
        port = int(params.get("port", 5432))
        with socket.create_connection((host, port), timeout=1):
            pass
    except OSError:
        raise unittest.SkipTest(
            "POSTGRES_TEST_DSN not set and default DSN is not reachable"
        )
    return POSTGRES_TEST_DSN


def reset_postgres_database(dsn):
    validate_test_dsn(dsn)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    apply_migrations(dsn, owner_role=None)


class PostgresDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        reset_postgres_database(POSTGRES_TEST_DSN)
        self.runtime_dsn = POSTGRES_TEST_DSN
