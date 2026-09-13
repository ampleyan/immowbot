import os
import tempfile
import unittest

from src.buyer.search_config import DEFAULT_HOME_SEARCH, normalize_search_config
from src.buyer.property_store import PropertyStore


class SearchConfigTest(unittest.TestCase):
    def test_defaults_match_the_approved_search(self):
        config = normalize_search_config(DEFAULT_HOME_SEARCH)
        self.assertEqual(config["postcodes"], ["2000", "2018"])
        self.assertEqual(config["property_types"], ["house", "apartment"])
        self.assertEqual(config["max_price"], 385000)
        self.assertEqual(config["min_surface_area"], 80)
        self.assertEqual(config["min_bedrooms"], 2)
        self.assertEqual(config["epc_labels"], ["A", "B", "C"])

    def test_normalization_does_not_mutate_the_input(self):
        original = {**DEFAULT_HOME_SEARCH, "postcodes": [" 2018 ", "2000", "2018"]}
        config = normalize_search_config(original)
        self.assertEqual(config["postcodes"], ["2018", "2000"])
        self.assertEqual(original["postcodes"], [" 2018 ", "2000", "2018"])

    def test_invalid_ranges_and_portals_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_search_config({**DEFAULT_HOME_SEARCH, "min_price": 400000, "max_price": 300000})
        with self.assertRaises(ValueError):
            normalize_search_config({**DEFAULT_HOME_SEARCH, "portals": ["unknown"]})


class PropertyStoreTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        self.store = PropertyStore(self.path)

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_search_and_run_keep_normalized_configuration(self):
        search_id = self.store.save_search("home", "home", DEFAULT_HOME_SEARCH)
        search = self.store.get_search(search_id)
        run_id = self.store.start_run(search_id)
        self.assertEqual(search["config"]["max_price"], 385000)
        self.assertEqual(self.store.get_run(run_id)["config"], search["config"])

    def test_identical_observation_does_not_create_a_version(self):
        run_id = self._start_run()
        listing = self._listing()
        self.store.save_listing(run_id, listing)
        self.store.save_listing(run_id, listing)
        self.assertEqual(self.store.version_count("immoweb", "123"), 1)

    def test_changed_observation_creates_a_version(self):
        run_id = self._start_run()
        listing = self._listing()
        self.store.save_listing(run_id, listing)
        self.store.save_listing(run_id, {**listing, "price": 290000})
        self.assertEqual(self.store.version_count("immoweb", "123"), 2)
        self.assertEqual(self.store.latest_listings("sale")[0]["price"], 290000)

    def _start_run(self):
        search_id = self.store.save_search("home", "home", DEFAULT_HOME_SEARCH)
        return self.store.start_run(search_id)

    def _listing(self):
        return {
            "source": "immoweb",
            "source_listing_id": "123",
            "url": "https://example.test/123",
            "transaction_type": "sale",
            "price": 300000,
            "postcode": "2000",
            "property_type": "apartment",
            "surface_area": 90,
            "bedrooms": 2,
            "epc_score": "B",
        }


if __name__ == "__main__":
    unittest.main()
