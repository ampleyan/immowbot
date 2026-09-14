import os
import tempfile
import unittest
from unittest.mock import patch

from src.buyer.collector import run_collection, run_selected_collection
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

    @patch("src.buyer.collector._translator.translate_property_description")
    def test_collection_stores_refreshed_english_description(self, translate):
        translate.return_value = {"translated": "English description"}
        raw = {**_make_raw("immoweb", "translation"), "description": "Fresh property description", "description_english": "Fresh property description"}
        run_collection(self.store, self.search_id, FakeScraper({"immoweb": [raw], "immoscoop": [], "zimmo": []}))
        saved = self.store.latest_listings("sale")[0]
        self.assertEqual(saved["description_english"], "English description")
        translate.assert_called_once_with("Fresh property description", target_language="en")

    def test_delta_mode_seeds_scraper_with_seen_urls(self):
        raw = _make_raw("immoweb", "seen")
        run_collection(self.store, self.search_id, FakeScraper({"immoweb": [raw], "immoscoop": [], "zimmo": []}))
        self.store.save_search("home", "home", {**DEFAULT_HOME_SEARCH, "scrape_mode": "delta"})

        class Scraper:
            def __init__(self):
                self.existing_properties = set()

        class Manager(FakeScraper):
            def __init__(self):
                super().__init__({"immoweb": [], "immoscoop": [], "zimmo": []})
                self.scraper = Scraper()

            def get_scraper(self, website):
                return self.scraper

        manager = Manager()
        run_collection(self.store, self.search_id, manager)
        self.assertIn(raw["url"], manager.scraper.existing_properties)

    def test_collection_persists_listings_after_each_batch_of_five_checks(self):
        class StreamingScraper:
            def scrape_website(self, website, on_listing, on_checked, **kwargs):
                listings = [_make_raw("immoweb", str(index)) for index in range(1, 8)]
                for listing in listings:
                    on_listing(listing)
                    on_checked()
                return listings

        search_id = self.store.save_search(
            "streaming-home", "home", {**DEFAULT_HOME_SEARCH, "portals": ["immoweb"]}
        )
        progress = []

        run_collection(self.store, search_id, StreamingScraper(), on_progress=progress.append)

        self.assertEqual([item["checked"] for item in progress], [5, 7])
        self.assertEqual([item["saved"] for item in progress], [5, 7])
        self.assertEqual(len(self.store.latest_listings("sale")), 7)

    def test_collection_cancellation_keeps_the_completed_batch(self):
        class StreamingScraper:
            def scrape_website(self, website, on_listing, on_checked, should_cancel, **kwargs):
                listings = [_make_raw("immoweb", str(index)) for index in range(1, 8)]
                for listing in listings:
                    if should_cancel():
                        break
                    on_listing(listing)
                    on_checked()
                return listings

        search_id = self.store.save_search(
            "cancelled-home", "home", {**DEFAULT_HOME_SEARCH, "portals": ["immoweb"]}
        )
        cancelled = False

        def should_cancel():
            return cancelled

        def on_progress(progress):
            nonlocal cancelled
            if progress["saved"] == 5:
                cancelled = True

        run_id = run_collection(
            self.store,
            search_id,
            StreamingScraper(),
            on_progress=on_progress,
            should_cancel=should_cancel,
        )

        self.assertEqual(self.store.get_run(run_id)["status"], "cancelled")
        self.assertEqual(len(self.store.latest_listings("sale")), 5)

    def test_selected_collection_only_rescrapes_requested_listings(self):
        class SelectedScraper:
            def scrape_selected_listings(self, selections, on_listing, on_checked, should_cancel):
                for selection in selections:
                    raw = _make_raw(selection["source"], selection["source_listing_id"])
                    raw["url"] = selection["url"]
                    on_listing(raw)
                    on_checked()

        selections = [
            {"source": "immoweb", "source_listing_id": "101", "url": "https://immoweb.be/listing/101"},
            {"source": "immoweb", "source_listing_id": "102", "url": "https://immoweb.be/listing/102"},
        ]
        run_id = run_selected_collection(self.store, self.search_id, SelectedScraper(), selections)

        self.assertEqual(self.store.get_run(run_id)["status"], "ok")
        saved = self.store.latest_listings("sale")
        self.assertEqual({listing["source_listing_id"] for listing in saved}, {"101", "102"})


if __name__ == "__main__":
    unittest.main()
