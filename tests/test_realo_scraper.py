import json
import unittest

from src.scrapers.realo_scraper import RealoScraper


class RealoScraperTest(unittest.TestCase):
    def setUp(self):
        self.scraper = RealoScraper()

    def test_build_search_url_translates_common_filters(self):
        url = self.scraper._build_search_url(
            min_price=150000,
            max_price=350000,
            min_surface=80,
            epc_scores=["A", "B"],
            postal_codes=["BE-2000", "9000"],
        )

        self.assertIn("offerType=for-sale", url)
        self.assertIn("priceMin=150000", url)
        self.assertIn("priceMax=350000", url)
        self.assertIn("surfaceMin=80", url)
        self.assertIn("postalCodes=2000%2C9000", url)
        self.assertIn("energyClasses=A%2CB", url)

    def test_extract_property_urls_ignores_navigation_links(self):
        html = """
        <a href="/nl/zoeken">Search</a>
        <a href="/nl/appartement/antwerpen/1234567">Apartment</a>
        <a href="https://www.realo.be/nl/huis/gent/7654321?foo=bar">House</a>
        <a href="/nl/nieuwbouwproject/ignore-me">Project</a>
        <a href="/nl/appartement/antwerpen/1234567">Duplicate</a>
        """

        self.assertEqual(
            self.scraper._extract_property_urls(html, self.scraper.base_url),
            [
                "https://www.realo.be/nl/appartement/antwerpen/1234567",
                "https://www.realo.be/nl/huis/gent/7654321",
            ],
        )

    def test_parse_property_html_reads_json_ld_listing_fields(self):
        payload = {
            "@type": "Residence",
            "name": "Bright apartment",
            "description": "A sunny home near the station.",
            "image": ["https://cdn.realo.be/image.jpg"],
            "offers": {"@type": "Offer", "price": "295000", "priceCurrency": "EUR"},
            "address": {
                "streetAddress": "Main Street 4",
                "addressLocality": "Antwerp",
                "postalCode": "2000",
            },
            "geo": {"latitude": "51.2194", "longitude": "4.4025"},
            "numberOfRooms": 2,
            "floorSize": {"value": 88, "unitText": "SQM"},
        }
        html = '<script type="application/ld+json">' + json.dumps(payload) + "</script>"

        result = self.scraper._parse_property_html(
            html, "https://www.realo.be/nl/appartement/antwerpen/1234567"
        )

        self.assertEqual(result["id"], "1234567")
        self.assertEqual(result["name"], "Bright apartment")
        self.assertEqual(result["price"], 295000)
        self.assertEqual(result["postcode"], "2000")
        self.assertEqual(result["bedrooms"], 2)
        self.assertEqual(result["surface_area"], 88)
        self.assertEqual(result["image_url_1"], "https://cdn.realo.be/image.jpg")


if __name__ == "__main__":
    unittest.main()
