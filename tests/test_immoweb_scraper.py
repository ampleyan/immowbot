import unittest

from src.scrapers.immoweb_scraper import ImmowebScraper


class ImmowebScraperTest(unittest.TestCase):
    def test_search_url_orders_newest_first_for_delta_crawls(self):
        scraper = ImmowebScraper.__new__(ImmowebScraper)

        url = scraper._build_search_url()

        self.assertIn("orderBy=newest", url)

    def test_classified_data_with_missing_sections_is_still_extracted(self):
        scraper = ImmowebScraper.__new__(ImmowebScraper)

        class Translator:
            def prepare_description(self, text):
                return {"original": text, "translated": "", "detected_language": "nl"}

            def translate_property_description(self, text):
                return {"original": text, "translated": "", "detected_language": "nl"}

        scraper.translator = Translator()
        result = scraper._extract_comprehensive_data_from_classified({
            "id": "21703622",
            "property": {"subtype": "apartment", "location": None, "kitchen": None, "energy": None, "land": None},
            "price": {"mainValue": 250000},
            "transaction": {"certificates": None, "sale": None},
            "flags": {"isUnderOption": False},
            "media": {"pictures": []},
        })

        self.assertEqual(result["id"], "21703622")
        self.assertEqual(result["images"], [])
        self.assertEqual(result["price"], 250000)

    def test_recognizes_under_option_from_flag_list_text(self):
        scraper = ImmowebScraper.__new__(ImmowebScraper)

        self.assertTrue(scraper._has_under_option_label(["New", " Under   option "]))
        self.assertFalse(scraper._has_under_option_label(["Sold", "New construction"]))


if __name__ == "__main__":
    unittest.main()
