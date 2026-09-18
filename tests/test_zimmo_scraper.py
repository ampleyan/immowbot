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
        <img src="https://files.zimmo.be/backend-api/token/listings/57f1f7f2-6b86-4dac-8a08-bfe6fd87b156/images/01.jpg">
        <img src="https://files.zimmo.be/backend-api/token/listings/57f1f7f2-6b86-4dac-8a08-bfe6fd87b156/images/02.jpg">
        """

        data = self.scraper._extract_zimmo_data(
            BeautifulSoup(html, "html.parser"),
            "https://www.zimmo.be/nl/antwerpen-2018/te-koop/appartement/LRPIV",
        )

        self.assertEqual(data["images"], [
            "https://files.zimmo.be/backend-api/token/listings/57f1f7f2-6b86-4dac-8a08-bfe6fd87b156/images/01.jpg",
            "https://files.zimmo.be/backend-api/token/listings/57f1f7f2-6b86-4dac-8a08-bfe6fd87b156/images/02.jpg",
        ])
        self.assertEqual(data["image_url_1"], "https://files.zimmo.be/backend-api/token/listings/57f1f7f2-6b86-4dac-8a08-bfe6fd87b156/images/01.jpg")

    def test_reveal_contact_details_clicks_visible_actions_and_extracts_values(self):
        class ContactAction:
            def __init__(self, label, driver):
                self.text = label
                self.driver = driver
                self.clicked = False

            def is_displayed(self):
                return True

            def click(self):
                self.clicked = True
                self.driver.revealed = True

        class Driver:
            def __init__(self):
                self.revealed = False
                self.phone_action = ContactAction("Bellen", self)
                self.email_action = ContactAction("Mailen", self)

            @property
            def page_source(self):
                if self.revealed:
                    return "<main>+32 3 555 12 34 agent@example.test</main>"
                return "<main>Contacteer de aanbieder</main>"

            def find_elements(self, by, selector):
                if selector == "button, a":
                    return [self.phone_action, self.email_action]
                return []

        driver = Driver()

        result = self.scraper._reveal_contact_details(driver)

        self.assertTrue(driver.phone_action.clicked)
        self.assertTrue(driver.email_action.clicked)
        self.assertEqual(result["agent_phone"], "+32 3 555 12 34")
        self.assertEqual(result["agent_email"], "agent@example.test")
        self.assertEqual(result["contact_status"], "available")
        self.assertTrue(result["contact_scraped_at"])

    def test_reveal_contact_details_returns_unavailable_without_contact_actions(self):
        class Driver:
            page_source = "<main>Geen contactgegevens beschikbaar</main>"

            def find_elements(self, by, selector):
                return []

        result = self.scraper._reveal_contact_details(Driver())

        self.assertEqual(result["agent_phone"], "")
        self.assertEqual(result["agent_email"], "")
        self.assertEqual(result["contact_status"], "unavailable")
        self.assertIsNone(result["contact_scraped_at"])

    def test_reveal_contact_details_returns_requires_login_without_clicking(self):
        class Driver:
            page_source = "<main>Log in om contactgegevens te bekijken</main>"

            def find_elements(self, by, selector):
                return []

        result = self.scraper._reveal_contact_details(Driver())

        self.assertEqual(result["agent_phone"], "")
        self.assertEqual(result["agent_email"], "")
        self.assertEqual(result["contact_status"], "requires_login")
        self.assertIsNone(result["contact_scraped_at"])

    def test_extract_agency_details_uses_structured_provider_data(self):
        html = """
        <script id="ng-state" type="application/json">
        {"LISTING_DETAIL_LRPIV":{"estate":{"agency":{"name":"Example Realty",
        "address":{"streetAddress":"Teststraat 4","postalCode":"2000",
        "addressLocality":"Antwerpen"},"url":"https://example.test/agency"}}}}
        </script>
        """

        result = self.scraper._extract_agency_details(BeautifulSoup(html, "html.parser"))

        self.assertEqual(result["agency_name"], "Example Realty")
        self.assertEqual(result["agency_address"], "Teststraat 4, 2000 Antwerpen")
        self.assertEqual(result["agency_url"], "https://example.test/agency")


if __name__ == "__main__":
    unittest.main()
