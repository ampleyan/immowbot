import unittest

from src.buyer.search_config import AVAILABLE_PORTALS, normalize_search_config, DEFAULT_HOME_SEARCH
from src.scraper_manager import ScraperFactory, ScraperManager


class PortalRegistryTest(unittest.TestCase):
    def test_new_portals_are_registered(self):
        self.assertIn("realo", AVAILABLE_PORTALS)
        self.assertIn("immovlan", AVAILABLE_PORTALS)
        manager = ScraperManager()
        self.assertIsNotNone(manager.get_scraper("realo"))
        self.assertIsNotNone(manager.get_scraper("immovlan"))
        self.assertEqual(ScraperManager.detect_website_from_url("https://www.realo.be/nl/huis/antwerpen/123"), "realo")
        self.assertEqual(ScraperManager.detect_website_from_url("https://immovlan.be/en/detail/house/abc123"), "immovlan")

    def test_default_config_accepts_new_portals(self):
        config = normalize_search_config({**DEFAULT_HOME_SEARCH, "portals": ["realo", "immovlan"]})
        self.assertEqual(config["portals"], ["realo", "immovlan"])

    def test_factory_creates_new_portals(self):
        self.assertEqual(ScraperFactory.create_scraper("realo").website_name, "Realo")
        self.assertEqual(ScraperFactory.create_scraper("immovlan").website_name, "Immovlan")


if __name__ == "__main__":
    unittest.main()
