import os
import unittest

import psycopg

from src.buyer.postgres_migrations import apply_migrations


TEST_DSN = os.getenv(
    "POSTGRES_TEST_DSN",
    "postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test",
)


class PostgresBaselineTest(unittest.TestCase):
    def setUp(self):
        with psycopg.connect(TEST_DSN, autocommit=True) as connection:
            connection.execute("DROP SCHEMA public CASCADE")
            connection.execute("CREATE SCHEMA public")

    def test_baseline_creates_domain_tables(self):
        apply_migrations(TEST_DSN, owner_role=None)
        with psycopg.connect(TEST_DSN) as connection:
            rows = connection.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ).fetchall()

        self.assertEqual(
            {row[0] for row in rows},
            {
                "alerts", "list_items", "listing_interactions", "listing_versions",
                "listing_workflow", "listings", "property_lists", "property_notes",
                "runs", "schema_migrations", "searches", "smart_lists", "source_runs", "users",
            },
        )


if __name__ == "__main__":
    unittest.main()
