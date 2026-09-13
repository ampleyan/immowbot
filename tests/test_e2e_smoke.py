import os
import tempfile
import unittest

from src.buyer.collector import run_collection
from src.buyer.property_scoring import calculate_home_score
from src.buyer.property_store import PropertyStore
from src.buyer.search_config import DEFAULT_HOME_SEARCH


class FakeScraper:
    def scrape_website(self, website, **kwargs):
        if website != "immoweb":
            return []
        return [
            {
                "id": "home-101",
                "url": "https://immoweb.be/en/classified/home-101",
                "source_website": "immoweb",
                "price": 300000,
                "postcode": "2000",
                "property_type": "house",
                "surface_area": 100,
                "bedrooms": 3,
                "epc_score": "B",
            },
            {
                "id": "home-102",
                "url": "https://immoweb.be/en/classified/home-102",
                "source_website": "immoweb",
                "price": 300000,
                "postcode": "2000",
                "property_type": "house",
                "surface_area": 100,
                "bedrooms": 3,
                "epc_score": "B",
            },
            {
                "id": "home-103",
                "url": "https://immoweb.be/en/classified/home-103",
                "source_website": "immoweb",
                "price": 300000,
                "postcode": "2000",
                "property_type": "house",
                "surface_area": 100,
                "bedrooms": 3,
                "epc_score": "B",
            },
        ]


class BuyerPipelineSmokeTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        self.store = PropertyStore(self.path)

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_collection_persists_and_scores_default_home_listings(self):
        search_id = self.store.save_search("antwerp-home", "home", DEFAULT_HOME_SEARCH)
        run_collection(self.store, search_id, FakeScraper())

        listings = self.store.latest_listings("sale")

        self.assertEqual(len(listings), 3)
        self.assertEqual({listing["source_listing_id"] for listing in listings}, {"home-101", "home-102", "home-103"})
        for listing in listings:
            self.assertIsNotNone(calculate_home_score(listing, DEFAULT_HOME_SEARCH)["score"])


if __name__ == "__main__":
    unittest.main()
