import unittest

from src.base_scraper import BasePropertyScraper


class TestScraper(BasePropertyScraper):
    def _build_search_url(self, *args, **kwargs):
        return ""

    def _extract_property_urls(self, *args, **kwargs):
        return []

    def _scrape_property_details(self, *args, **kwargs):
        return None

    def scrape_from_url(self, *args, **kwargs):
        return []

    def scrape_with_filters(self, *args, **kwargs):
        return []


class BaseScraperTest(unittest.TestCase):
    def setUp(self):
        self.scraper = TestScraper.__new__(TestScraper)
        self.scraper.website_name = "test"

    def test_normalizes_responsive_image_objects_to_all_urls(self):
        normalized = self.scraper._normalize_property_data({
            "name": "Test property",
            "url": "https://example.test/listing/1",
            "price": 250000,
            "postcode": "2000",
            "image_url_1": {"url": "https://img.example/one.jpg", "sizes": {"1024": "https://img.example/one-large.jpg"}},
            "images": [
                {"url": "https://img.example/one.jpg"},
                {"sizes": {"1280": "https://img.example/two.jpg"}},
            ],
        })

        self.assertEqual(normalized["image_url_1"], "https://img.example/one.jpg")
        self.assertEqual(normalized["image_url_2"], "https://img.example/two.jpg")
        self.assertEqual(normalized["images"], ["https://img.example/one.jpg", "https://img.example/two.jpg"])

    def test_normalizes_outdoor_features_from_portal_detail_labels(self):
        normalized = self.scraper._normalize_property_data({
            "name": "Garden home",
            "url": "https://example.test/listing/2",
            "price": 300000,
            "postcode": "2000",
            "all_property_details": {"Garden": "Yes", "Terrace surface": "18 m²"},
        })

        self.assertTrue(normalized["outdoor_garden"])
        self.assertFalse(normalized["outdoor_terrace"])
        self.assertEqual(normalized["outdoor_surface"], 18)

    def test_preserves_under_option_flag(self):
        normalized = self.scraper._normalize_property_data({
            "name": "Reserved home",
            "url": "https://example.test/listing/3",
            "price": 300000,
            "postcode": "2000",
            "under_option": True,
        })

        self.assertTrue(normalized["under_option"])


if __name__ == "__main__":
    unittest.main()
