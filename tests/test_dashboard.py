import os
import tempfile
import threading
import unittest

from src.buyer import dashboard


class DashboardStoreTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        self.original_path = dashboard.DB_PATH
        dashboard.DB_PATH = self.path
        getattr(dashboard.get_store, "clear", lambda: None)()

    def tearDown(self):
        getattr(dashboard.get_store, "clear", lambda: None)()
        dashboard.DB_PATH = self.original_path
        os.unlink(self.path)

    def test_store_is_usable_from_a_later_streamlit_thread(self):
        main_store = dashboard.get_store()
        errors = []

        def use_store():
            try:
                worker_store = dashboard.get_store()
                worker_store.list_searches()
                worker_store.close()
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=use_store)
        worker.start()
        worker.join()
        main_store.close()

        self.assertEqual(errors, [])

    def test_listing_image_urls_are_ordered_and_ignore_empty_values(self):
        urls = dashboard._listing_image_urls({
            "image_url_1": "https://example.test/one.jpg",
            "image_url_2": "",
            "images": ["https://example.test/three.jpg"],
        })

        self.assertEqual(urls, ["https://example.test/one.jpg", "https://example.test/three.jpg"])

    def test_listing_image_urls_falls_back_to_all_property_details(self):
        urls = dashboard._listing_image_urls({
            "all_property_details": {
                "Image 1 URL": "https://example.test/detail1.jpg",
                "Image 2 URL": "https://example.test/detail2.jpg",
            }
        })

        self.assertEqual(urls, ["https://example.test/detail1.jpg", "https://example.test/detail2.jpg"])

    def test_listing_image_urls_deduplicates_across_sources(self):
        urls = dashboard._listing_image_urls({
            "image_url_1": "https://example.test/same.jpg",
            "all_property_details": {"Image 1 URL": "https://example.test/same.jpg"},
        })

        self.assertEqual(urls, ["https://example.test/same.jpg"])


if __name__ == "__main__":
    unittest.main()
