import os
import unittest
from unittest.mock import patch

from src.buyer import api
from src.buyer.database import DatabaseSettings
from src.buyer.property_store import PropertyStore
from src.buyer.search_config import DEFAULT_HOME_SEARCH
from tests.postgres_support import PostgresDatabaseTestCase, postgres_test_dsn


def postgres_local_environ(dsn):
    """Return an env dict that makes load_database_settings() return a local-mode DSN for testing."""
    return {
        "DATABASE_MODE": "local",
        "DATABASE_DSN": dsn,
    }


class ApiDatabaseIntegrationTest(PostgresDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.store = PropertyStore(self.runtime_dsn)

    def tearDown(self):
        self.store.close()

    def test_api_store_uses_validated_database_settings(self):
        with patch.dict(os.environ, postgres_local_environ(self.runtime_dsn), clear=True):
            store = api.get_store()
        self.addCleanup(store.close)
        self.assertEqual(store.get_search_by_name(1, "antwerp-home"), None)

    def test_run_history_is_returned_without_dashboard_sqlite_aggregation(self):
        user_id = self.store.create_user("testuser", "password123", is_admin=False)
        search_id = self.store.save_search(user_id, "antwerp-home", "home", DEFAULT_HOME_SEARCH)
        run_id = self.store.start_run(search_id)
        self.store.record_source_result(run_id, "immoweb", "ok", 2)
        listing = {
            "source": "immoweb",
            "source_listing_id": "123",
            "url": "https://immoweb.be/123",
            "transaction_type": "sale",
            "price": 200000,
            "postcode": "2000",
        }
        self.store.save_listing(run_id, listing)
        self.store.finish_run(run_id, "ok")

        rows = self.store.get_runs_with_sources(search_id, limit=5)
        self.assertEqual(rows[0]["sources"][0], {"source": "immoweb", "status": "ok", "count": 2})


if __name__ == "__main__":
    unittest.main()
