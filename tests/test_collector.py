import os
import tempfile
import unittest

from src.buyer.collector import run_collection
from src.buyer.property_store import PropertyStore
from src.buyer.search_config import DEFAULT_HOME_SEARCH


def _make_raw(portal, listing_id, price=300000, epc="B"):
    return {
        "id": listing_id,
        "url": f"https://{portal}.be/listing/{listing_id}",
        "source_website": portal,
        "price": price,
        "postcode": "2000",
        "property_type": "apartment",
        "surface_area": 90,
        "bedrooms": 2,
        "epc_score": epc,
    }


class FakeScraper:
    def __init__(self, results_by_portal):
        self._results = results_by_portal

    def scrape_website(self, website, **kwargs):
        return self._results.get(website, [])


class CollectorTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        self.store = PropertyStore(self.path)
        self.search_id = self.store.save_search("home", "home", DEFAULT_HOME_SEARCH)

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_successful_collection_saves_listings_and_marks_run_ok(self):
        scraper = FakeScraper({
            "immoweb": [_make_raw("immoweb", "101"), _make_raw("immoweb", "102")],
            "immoscoop": [_make_raw("immoscoop", "201")],
            "zimmo": [],
        })
        run_id = run_collection(self.store, self.search_id, scraper)
        run = self.store.get_run(run_id)
        listings = self.store.latest_listings("sale")
        self.assertEqual(run["status"], "ok")
        self.assertEqual(len(listings), 3)

    def test_one_portal_failure_does_not_stop_others(self):
        class PartialScraper:
            def scrape_website(self, website, **kwargs):
                if website == "immoscoop":
                    raise RuntimeError("network error")
                return [_make_raw(website, "999")]

        run_id = run_collection(self.store, self.search_id, PartialScraper())
        run = self.store.get_run(run_id)
        listings = self.store.latest_listings("sale")
        self.assertEqual(run["status"], "partial")
        self.assertEqual(len(listings), 2)

    def test_listings_with_missing_required_fields_are_skipped(self):
        bad = {"id": "bad", "url": "https://immoweb.be/bad", "source_website": "immoweb"}
        scraper = FakeScraper({"immoweb": [bad], "immoscoop": [], "zimmo": []})
        run_collection(self.store, self.search_id, scraper)
        self.assertEqual(len(self.store.latest_listings("sale")), 0)

    def test_duplicate_listing_across_runs_creates_one_version(self):
        raw = _make_raw("immoweb", "555")
        scraper = FakeScraper({"immoweb": [raw], "immoscoop": [], "zimmo": []})
        run_collection(self.store, self.search_id, scraper)
        run_collection(self.store, self.search_id, scraper)
        self.assertEqual(self.store.version_count("immoweb", "555"), 1)


if __name__ == "__main__":
    unittest.main()
