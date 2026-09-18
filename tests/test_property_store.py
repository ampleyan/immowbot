import unittest

from src.buyer.search_config import DEFAULT_HOME_SEARCH, normalize_search_config
from src.buyer.property_store import PropertyStore, _normalized_listing_fingerprint
from tests.postgres_support import PostgresDatabaseTestCase


class SearchConfigTest(unittest.TestCase):
    def test_translated_description_does_not_change_listing_fingerprint(self):
        listing = {"description": "Original text", "description_english": "Old translation", "price": 300000}
        translated = {**listing, "description_english": "New translation"}
        self.assertEqual(_normalized_listing_fingerprint(listing), _normalized_listing_fingerprint(translated))

    def test_defaults_match_the_approved_search(self):
        config = normalize_search_config(DEFAULT_HOME_SEARCH)
        self.assertEqual(config["postcodes"], ["2000", "2018"])
        self.assertEqual(config["property_types"], ["house", "apartment"])
        self.assertEqual(config["max_price"], 385000)
        self.assertEqual(config["min_surface_area"], 80)
        self.assertEqual(config["min_bedrooms"], 2)
        self.assertEqual(config["epc_labels"], ["A", "B", "C"])
        self.assertEqual(config["score_weights"], {"price": 30, "surface_area": 25, "bedrooms": 15, "epc": 20, "completeness": 10})
        self.assertEqual(config["outdoor_features"], [])
        self.assertEqual(config["building_age"], "any")

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
        with self.assertRaises(ValueError):
            normalize_search_config({**DEFAULT_HOME_SEARCH, "building_age": "unknown"})
        with self.assertRaises(ValueError):
            normalize_search_config({**DEFAULT_HOME_SEARCH, "min_construction_year": 2020, "max_construction_year": 2010})
        with self.assertRaises(ValueError):
            normalize_search_config({**DEFAULT_HOME_SEARCH, "score_weights": {"price": 100}})

    def test_outdoor_and_building_preferences_are_normalized(self):
        config = normalize_search_config({
            **DEFAULT_HOME_SEARCH,
            "outdoor_features": [" Terrace ", "garden", "terrace"],
            "building_age": "project",
            "min_construction_year": "2015",
        })
        self.assertEqual(config["outdoor_features"], ["terrace", "garden"])
        self.assertEqual(config["building_age"], "project")
        self.assertEqual(config["min_construction_year"], 2015)


class PropertyStoreTest(PostgresDatabaseTestCase):
    user_id = 1

    def setUp(self):
        super().setUp()
        self.store = PropertyStore(self.runtime_dsn)

    def tearDown(self):
        self.store.close()

    def test_search_and_run_keep_normalized_configuration(self):
        search_id = self.store.save_search(self.user_id, "home", "home", DEFAULT_HOME_SEARCH)
        search = self.store.get_search(search_id)
        run_id = self.store.start_run(search_id)
        self.assertEqual(search["config"]["max_price"], 385000)
        self.assertEqual(self.store.get_run(run_id)["config"], search["config"])

    def test_save_search_returns_integer_id(self):
        search_id = self.store.save_search(self.user_id, "home", "home", DEFAULT_HOME_SEARCH)
        self.assertIsInstance(search_id, int)
        self.assertGreater(search_id, 0)

    def test_start_run_returns_integer_id(self):
        search_id = self.store.save_search(self.user_id, "home", "home", DEFAULT_HOME_SEARCH)
        run_id = self.store.start_run(search_id)
        self.assertIsInstance(run_id, int)
        self.assertGreater(run_id, 0)

    def test_identical_observation_does_not_create_a_version(self):
        search_id = self.store.save_search(self.user_id, "home", "home", DEFAULT_HOME_SEARCH)
        run_id = self.store.start_run(search_id)
        self.store.save_listing(run_id, self.listing())
        self.store.save_listing(run_id, self.listing())
        self.assertEqual(self.store.version_count("immoweb", "123"), 1)

    def test_changed_observation_creates_a_version(self):
        run_id = self._start_run()
        listing = self.listing()
        self.store.save_listing(run_id, listing)
        self.store.save_listing(run_id, {**listing, "price": 290000})
        self.assertEqual(self.store.version_count("immoweb", "123"), 2)
        self.assertEqual(self.store.latest_listings("sale")[0]["price"], 290000)

    def test_price_reduced_flag_from_jsonb(self):
        run_id = self._start_run()
        listing = self.listing()
        self.store.save_listing(run_id, listing)
        self.store.save_listing(run_id, {**listing, "price": 250000})
        listings = self.store.latest_listings("sale")
        self.assertTrue(listings[0]["_price_reduced"])

    def test_rescrape_extends_existing_image_gallery(self):
        run_id = self._start_run()
        listing = {**self.listing(), "images": ["https://example.test/one.jpg"], "image_url_1": "https://example.test/one.jpg"}
        self.store.save_listing(run_id, listing)
        self.store.save_listing(run_id, {**listing, "images": ["https://example.test/two.jpg"], "image_url_1": "https://example.test/two.jpg", "image_url_2": None})
        saved = self.store.latest_listings("sale")[0]
        self.assertEqual(saved["images"], ["https://example.test/one.jpg", "https://example.test/two.jpg"])
        self.assertEqual(saved["image_url_1"], "https://example.test/one.jpg")
        self.assertEqual(saved["image_url_2"], "https://example.test/two.jpg")

    def test_rescrape_updates_description_translation(self):
        run_id = self._start_run()
        self.store.save_listing(run_id, {**self.listing(), "description": "Oude beschrijving", "description_english": "Old description"})
        self.store.save_listing(run_id, {**self.listing(), "description": "Nieuwe beschrijving", "description_english": "New description"})
        saved = self.store.latest_listings("sale")[0]
        self.assertEqual(saved["description"], "Nieuwe beschrijving")
        self.assertEqual(saved["description_english"], "New description")

    def test_latest_listings_include_first_seen_at(self):
        run_id = self._start_run()
        self.store.save_listing(run_id, self.listing())
        first_seen = self.store.latest_listings("sale")[0]["_first_seen_at"]
        self.assertTrue(first_seen)
        self.assertIsInstance(first_seen, str)

    def test_timestamps_are_iso8601_strings(self):
        search_id = self.store.save_search(self.user_id, "home", "home", DEFAULT_HOME_SEARCH)
        run_id = self.store.start_run(search_id)
        run = self.store.get_run(run_id)
        self.assertIsInstance(run["started_at"], str)
        self.assertIn("T", run["started_at"])

    def test_save_search_is_idempotent(self):
        id1 = self.store.save_search(self.user_id, "home", "home", DEFAULT_HOME_SEARCH)
        id2 = self.store.save_search(self.user_id, "home", "home", DEFAULT_HOME_SEARCH)
        self.assertEqual(id1, id2)

    def _start_run(self):
        search_id = self.store.save_search(self.user_id, "home", "home", DEFAULT_HOME_SEARCH)
        return self.store.start_run(search_id)

    def listing(self):
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


class PropertyListsTest(PostgresDatabaseTestCase):
    user_id = 1

    def setUp(self):
        super().setUp()
        self.store = PropertyStore(self.runtime_dsn)
        search_id = self.store.save_search(self.user_id, "home", "home", DEFAULT_HOME_SEARCH)
        run_id = self.store.start_run(search_id)
        self.store.save_listing(run_id, {
            "source": "immoweb", "source_listing_id": "A1",
            "url": "https://ex.test/A1", "transaction_type": "sale",
            "price": 300000, "postcode": "2000",
        })

    def tearDown(self):
        self.store.close()

    def test_create_and_get_lists(self):
        self.store.create_list(self.user_id, "Favourites")
        self.store.create_list(self.user_id, "To visit")
        lists = self.store.get_lists(self.user_id)
        self.assertEqual(len(lists), 2)
        self.assertEqual({l["name"] for l in lists}, {"Favourites", "To visit"})

    def test_add_and_remove_from_list(self):
        list_id = self.store.create_list(self.user_id, "Shortlist")
        self.store.add_to_list(self.user_id, list_id, "immoweb", "A1")
        ids = self.store.get_property_list_ids(self.user_id, "immoweb", "A1")
        self.assertIn(list_id, ids)

        self.store.remove_from_list(self.user_id, list_id, "immoweb", "A1")
        ids = self.store.get_property_list_ids(self.user_id, "immoweb", "A1")
        self.assertNotIn(list_id, ids)

    def test_add_duplicate_is_idempotent(self):
        list_id = self.store.create_list(self.user_id, "Dupe test")
        self.store.add_to_list(self.user_id, list_id, "immoweb", "A1")
        self.store.add_to_list(self.user_id, list_id, "immoweb", "A1")
        items = self.store.get_list_items(self.user_id, list_id)
        self.assertEqual(len(items), 1)

    def test_delete_list_cascades(self):
        list_id = self.store.create_list(self.user_id, "Temp")
        self.store.add_to_list(self.user_id, list_id, "immoweb", "A1")
        self.store.delete_list(self.user_id, list_id)
        self.assertEqual(self.store.get_lists(self.user_id), [])
        self.assertEqual(self.store.get_property_list_ids(self.user_id, "immoweb", "A1"), set())

    def test_get_list_items_returns_payloads(self):
        list_id = self.store.create_list(self.user_id, "Full")
        self.store.add_to_list(self.user_id, list_id, "immoweb", "A1")
        items = self.store.get_list_items(self.user_id, list_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "immoweb")

    def test_item_count_in_get_lists(self):
        list_id = self.store.create_list(self.user_id, "Counted")
        self.assertEqual(self.store.get_lists(self.user_id)[0]["item_count"], 0)
        self.store.add_to_list(self.user_id, list_id, "immoweb", "A1")
        self.assertEqual(self.store.get_lists(self.user_id)[0]["item_count"], 1)


class PropertyNotesTest(PostgresDatabaseTestCase):
    user_id = 1

    def setUp(self):
        super().setUp()
        self.store = PropertyStore(self.runtime_dsn)

    def tearDown(self):
        self.store.close()

    def test_save_and_get_note(self):
        self.store.save_note(self.user_id, "immoweb", "A1", "Nice garden")
        self.assertEqual(self.store.get_note(self.user_id, "immoweb", "A1"), "Nice garden")

    def test_update_note(self):
        self.store.save_note(self.user_id, "immoweb", "A1", "First")
        self.store.save_note(self.user_id, "immoweb", "A1", "Updated")
        self.assertEqual(self.store.get_note(self.user_id, "immoweb", "A1"), "Updated")

    def test_get_note_missing_returns_empty(self):
        self.assertEqual(self.store.get_note(self.user_id, "immoweb", "NOPE"), "")

    def test_get_all_notes(self):
        self.store.save_note(self.user_id, "immoweb", "A1", "First note")
        self.store.save_note(self.user_id, "zimmo", "B2", "Second note")
        notes = self.store.get_all_notes(self.user_id)
        self.assertEqual(notes[("immoweb", "A1")], "First note")
        self.assertEqual(notes[("zimmo", "B2")], "Second note")


if __name__ == "__main__":
    unittest.main()
