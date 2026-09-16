import unittest

from src.buyer.collector import run_collection
from src.buyer.property_scoring import calculate_home_score
from src.buyer.property_store import PropertyStore
from src.buyer.search_config import DEFAULT_HOME_SEARCH
from tests.postgres_support import PostgresDatabaseTestCase

SINGLE_PORTAL_SEARCH = {
    **DEFAULT_HOME_SEARCH,
    "portals": ["immoweb"],
}

FAKE_LISTINGS = [
    {
        "id": "fake-001",
        "url": "https://example.test/1",
        "price": 280000,
        "postcode": "2000",
        "property_type": "house",
        "surface_area": 120,
        "bedrooms": 3,
        "epc_score": "B",
        "image_url_1": "https://example.test/img1.jpg",
        "image_url_2": "https://example.test/img1b.jpg",
    },
    {
        "id": "fake-002",
        "url": "https://example.test/2",
        "price": 350000,
        "postcode": "2018",
        "property_type": "apartment",
        "surface_area": 95,
        "bedrooms": 2,
        "epc_score": "A",
        "image_url_1": "https://example.test/img2.jpg",
    },
    {
        "id": "fake-003",
        "url": "https://example.test/3",
        "price": 420000,
        "postcode": "2000",
        "property_type": "house",
        "surface_area": 85,
        "bedrooms": 2,
        "epc_score": "C",
    },
]


class FakeScraper:
    def scrape_website(self, website, **kwargs):
        return list(FAKE_LISTINGS)


class E2ESmokeTest(PostgresDatabaseTestCase):
    user_id = 1

    def setUp(self):
        super().setUp()
        self.store = PropertyStore(self.runtime_dsn)
        self.search_id = self.store.save_search(self.user_id, "test-search", "home", SINGLE_PORTAL_SEARCH)

    def tearDown(self):
        self.store.close()

    def test_full_pipeline_stores_all_listings(self):
        run_collection(self.store, self.search_id, FakeScraper())
        listings = self.store.latest_listings("sale")
        self.assertEqual(len(listings), 3)
        urls = {l["url"] for l in listings}
        self.assertIn("https://example.test/1", urls)
        self.assertIn("https://example.test/2", urls)
        self.assertIn("https://example.test/3", urls)

    def test_full_pipeline_run_status_is_ok(self):
        run_id = run_collection(self.store, self.search_id, FakeScraper())
        run = self.store.get_run(run_id)
        self.assertEqual(run["status"], "ok")

    def test_scores_computed_for_all_stored_listings(self):
        run_collection(self.store, self.search_id, FakeScraper())
        config = self.store.get_search(self.search_id)["config"]
        listings = self.store.latest_listings("sale")
        self.assertEqual(len(listings), 3)
        for listing in listings:
            result = calculate_home_score(listing, config)
            self.assertIn("score", result)
            self.assertIn("components", result)
            self.assertIn("exclusions", result)

    def test_images_preserved_in_stored_listings(self):
        run_collection(self.store, self.search_id, FakeScraper())
        listings = self.store.latest_listings("sale")
        with_img = [l for l in listings if l.get("image_url_1")]
        self.assertGreaterEqual(len(with_img), 2)

    def test_second_run_does_not_duplicate_listings(self):
        run_collection(self.store, self.search_id, FakeScraper())
        run_collection(self.store, self.search_id, FakeScraper())
        listings = self.store.latest_listings("sale")
        self.assertEqual(len(listings), 3)


if __name__ == "__main__":
    unittest.main()
