import unittest

from bs4 import BeautifulSoup

from src.scrapers.immovlan_scraper import ImmovlanScraper


class ImmovlanScraperTest(unittest.TestCase):
    def setUp(self):
        self.scraper = ImmovlanScraper.__new__(ImmovlanScraper)
        self.scraper.base_url = "https://immovlan.be"

    def test_build_search_url_encodes_supported_filters(self):
        url = self.scraper._build_search_url(
            min_price=100000,
            max_price=350000,
            min_surface=80,
            epc_scores=["A", "B"],
            postal_codes=["BE-2000", "1000"],
        )

        self.assertIn("transactiontypes=for-sale", url)
        self.assertIn("minprice=100000", url)
        self.assertIn("maxprice=350000", url)
        self.assertIn("minlivablesurface=80", url)
        self.assertIn("energyclasses=A%2CB", url)
        self.assertIn("postalcode=2000%2C1000", url)

    def test_extract_property_urls_reads_cards_and_deduplicates(self):
        html = """
        <a class="v3-property-card" href="/en/detail/apartment/for-sale/2000/antwerp/abc123">One</a>
        <a class="v3-property-card" href="https://immovlan.be/en/detail/house/for-sale/1000/brussels/xyz789?foo=bar">Two</a>
        <a class="v3-property-card" href="/en/detail/apartment/for-sale/2000/antwerp/abc123">Duplicate</a>
        <a href="/en/real-estate/apartment">Not a listing</a>
        """

        urls = self.scraper._extract_property_urls(html, self.scraper.base_url)

        self.assertEqual(urls, [
            "https://immovlan.be/en/detail/apartment/for-sale/2000/antwerp/abc123",
            "https://immovlan.be/en/detail/house/for-sale/1000/brussels/xyz789",
        ])

    def test_extract_data_prefers_real_estate_listing_json_ld(self):
        html = """
        <script type="application/ld+json">
        {"@type":"RealEstateListing","name":"Apartment for sale in Antwerp",
         "description":"Bright apartment", "image":["https://img/one.jpg"],
         "mainEntity":{"@type":"Apartment","address":{"streetAddress":"Main 1",
         "addressLocality":"Antwerp","postalCode":"2000"},"geo":{"latitude":51.2,
         "longitude":4.4},"floorSize":{"value":95},"numberOfBedrooms":2,
         "numberOfBathroomsTotal":1,"yearBuilt":2010},
         "offers":{"price":299000,"priceCurrency":"EUR"}}
        </script>
        """

        data = self.scraper._extract_immovlan_data(
            BeautifulSoup(html, "html.parser"),
            "https://immovlan.be/en/detail/apartment/for-sale/2000/antwerp/abc123",
        )

        self.assertEqual(data["id"], "ABC123")
        self.assertEqual(data["price"], 299000)
        self.assertEqual(data["surface_area"], 95)
        self.assertEqual(data["bedrooms"], 2)
        self.assertEqual(data["postcode"], "2000")
        self.assertEqual(data["property_type"], "apartment")
        self.assertEqual(data["image_url_1"], "https://img/one.jpg")


if __name__ == "__main__":
    unittest.main()
