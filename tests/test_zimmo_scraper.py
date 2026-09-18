import unittest

from bs4 import BeautifulSoup

from src.scrapers.zimmo_scraper import ZimmoScraper


class TranslatorStub:
    def prepare_description(self, description):
        return {
            "translated": description,
            "detected_language": "nl",
        }


class ZimmoScraperTest(unittest.TestCase):
    def setUp(self):
        self.scraper = ZimmoScraper.__new__(ZimmoScraper)
        self.scraper.translator = TranslatorStub()

    def test_ng_state_path_keeps_gallery_images(self):
        html = """
        <script id="ng-state" type="application/json">
        {"LISTING_DETAIL_LRPIV":{"estate":{"id":"LRPIV","price":{"value":345000},
        "location":{"street":"Schulstraat","streetNumber":"17","postalCode":"2018",
        "locality":{"en":"Antwerpen"}},"floorspaceSurface":{"value":87}}}}
        </script>
        <img src="https://files.zimmo.be/property-photo-1.jpg">
        <img src="https://files.zimmo.be/property-photo-2.jpg">
        """

        data = self.scraper._extract_zimmo_data(
            BeautifulSoup(html, "html.parser"),
            "https://www.zimmo.be/nl/antwerpen-2018/te-koop/appartement/LRPIV",
        )

        self.assertEqual(data["images"], [
            "https://files.zimmo.be/property-photo-1.jpg",
            "https://files.zimmo.be/property-photo-2.jpg",
        ])
        self.assertEqual(data["image_url_1"], "https://files.zimmo.be/property-photo-1.jpg")


if __name__ == "__main__":
    unittest.main()
