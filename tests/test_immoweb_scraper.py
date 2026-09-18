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

    def test_reveals_and_extracts_immoweb_contact_details(self):
        scraper = ImmowebScraper.__new__(ImmowebScraper)

        class Button:
            text = "See phone number"

            def __init__(self):
                self.clicked = False

            def click(self):
                self.clicked = True

        class Card:
            text = "Contact agent +32 3 555 12 34 agent@example.be"

        class Driver:
            def __init__(self):
                self.button = Button()

            def find_elements(self, by, selector):
                if selector == ".customer-card__actions button":
                    return [self.button]
                if selector == ".customer-card":
                    return [Card()]
                return []

            def execute_script(self, script, element):
                return None

        driver = Driver()
        contacts = scraper._reveal_contact_details(driver)

        self.assertTrue(driver.button.clicked)
        self.assertEqual(contacts["agent_phone"], "+32 3 555 12 34")
        self.assertEqual(contacts["agent_email"], "agent@example.be")


if __name__ == "__main__":
    unittest.main()
