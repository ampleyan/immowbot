import io
import unittest
from contextlib import redirect_stdout

from bs4 import BeautifulSoup

from src.scrapers.immoscoop_scraper import ImmoscoopScraper
from src.scrapers.immoweb_scraper import ImmowebScraper
from src.scrapers.zimmo_scraper import ZimmoScraper


SHARED_KEYS = {
    "source_created_at", "source_updated_at", "agent_name", "agent_phone",
    "agent_email", "agency_name", "agency_address", "agency_url", "bathrooms",
    "contact_status", "contact_scraped_at",
    "floor", "epc_value", "epc_certificate_number", "heating_type",
    "renovation_obligation", "renovation_year", "monthly_charges",
    "cadastral_income", "parking", "terrace", "garden", "solar_panels",
    "investment_property", "new_build", "p_score", "g_score",
}


class TranslatorStub:
    def prepare_description(self, description):
        return {
            "original": description,
            "translated": description,
            "detected_language": "nl",
        }


class SourceDataContractTest(unittest.TestCase):
    def _normalized(self, scraper, raw_data):
        scraper.website_name = "test"
        return scraper._normalize_property_data(raw_data)

    def test_normalization_preserves_contact_metadata(self):
        scraper = ZimmoScraper.__new__(ZimmoScraper)

        normalized = self._normalized(scraper, {
            "name": "Test listing",
            "url": "https://www.zimmo.be/nl/test",
            "price": 300000,
            "location": "Antwerpen",
            "contact_status": "available",
            "contact_scraped_at": "2026-09-18T10:00:00",
        })

        self.assertEqual(normalized["contact_status"], "available")
        self.assertEqual(normalized["contact_scraped_at"], "2026-09-18T10:00:00")

    def test_immoweb_classified_payload_normalizes_public_facts(self):
        scraper = ImmowebScraper.__new__(ImmowebScraper)
        scraper.translator = TranslatorStub()
        raw_data = scraper._extract_comprehensive_data_from_classified({
            "createdAt": "2026-09-01T10:00:00Z",
            "updatedAt": "2026-09-12T11:00:00Z",
            "property": {
                "subtype": "apartment",
                "bedroomCount": 2,
                "bathroomCount": 1,
                "monthlyCosts": 175,
                "hasTerrace": True,
                "hasGarden": False,
                "parkingCountIndoor": 1,
                "isInvestmentProperty": True,
                "location": {"floor": 3},
                "building": {"constructionYear": 2018},
                "energy": {"heatingType": "gas", "hasPhotovoltaicPanels": True},
            },
            "price": {"mainValue": 350000},
            "transaction": {
                "certificates": {
                    "epcScore": "B",
                    "primaryEnergyConsumptionPerSqm": 114,
                    "epcReference": "20260901-0000001234-RES-1",
                    "renovationObligation": False,
                },
                "sale": {"cadastralIncome": 1200},
            },
            "flags": {"isNewlyBuilt": True, "isUnderOption": False},
            "media": {"pictures": []},
        })

        normalized = self._normalized(scraper, raw_data)

        self.assertTrue(SHARED_KEYS.issubset(normalized))
        self.assertEqual(normalized["floor"], 3)
        self.assertEqual(normalized["epc_value"], 114)
        self.assertEqual(normalized["epc_certificate_number"], "20260901-0000001234-RES-1")
        self.assertEqual(normalized["heating_type"], "gas")
        self.assertEqual(normalized["monthly_charges"], 175)
        self.assertEqual(normalized["cadastral_income"], 1200)
        self.assertTrue(normalized["solar_panels"])
        self.assertTrue(normalized["investment_property"])
        self.assertTrue(normalized["new_build"])
        self.assertIsNone(normalized["agency_name"])
        self.assertIn("all_property_details", normalized)

    def test_immoscoop_detail_groups_normalize_public_facts(self):
        scraper = ImmoscoopScraper.__new__(ImmoscoopScraper)
        scraper.translator = TranslatorStub()
        with redirect_stdout(io.StringIO()):
            raw_data = scraper._extract_from_next_data({
            "props": {"pageProps": {"property": {
                "id": "immo-1",
                "title": "Family home",
                "price": {"label": "€425,000"},
                "address": {"postalCode": "2000", "city": {"label": "Antwerp"}},
                "agent": {"name": "Eva Agent", "phone": "+32 3 555 00 00", "email": "eva@example.test"},
                "features": [{"id": "BathroomNumber", "value": "2"}],
                "propertyDetailGroups": [
                    {"group": "financial", "propertyDetails": [
                        {"title": "Monthly charges", "description": "€95"},
                        {"title": "Cadastral income", "description": "€780"},
                    ]},
                    {"group": "energy", "propertyDetails": [
                        {"title": "Heating type", "description": "Gas"},
                        {"title": "EPC value", "description": "156 kWh/m²"},
                    ]},
                    {"group": "location", "propertyDetails": [
                        {"title": "P-score", "description": "A"},
                        {"title": "G-score", "description": "B"},
                    ]},
                    {"group": "comfort", "propertyDetails": [
                        {"title": "Terrace", "description": "No"},
                    ]},
                ],
            }}},
            }, "https://www.immoscoop.be/en/for-sale/2000-antwerp/1")

        normalized = self._normalized(scraper, raw_data)

        self.assertTrue(SHARED_KEYS.issubset(normalized))
        self.assertEqual(normalized["agent_name"], "Eva Agent")
        self.assertEqual(normalized["monthly_charges"], "€95")
        self.assertEqual(normalized["heating_type"], "Gas")
        self.assertEqual(normalized["epc_value"], "156 kWh/m²")
        self.assertEqual(normalized["p_score"], "A")
        self.assertEqual(normalized["g_score"], "B")
        self.assertFalse(normalized["terrace"])
        self.assertIsNone(normalized["agency_name"])
        self.assertIn("property_details", normalized)
        self.assertIn("energy_details", normalized)

    def test_zimmo_ng_state_normalizes_public_facts_without_guesses(self):
        scraper = ZimmoScraper.__new__(ZimmoScraper)
        raw_data = scraper._parse_ng_state(BeautifulSoup('''
            <script id="ng-state" type="application/json">
            {"LISTING_DETAIL_ZIMMO1":{"estate":{"id":"ZIMMO1","price":{"value":299000},
            "bathroomsCount":1,"createdAt":"2026-09-01T10:00:00Z","updatedAt":"2026-09-14T10:00:00Z",
            "location":{"street":"Teststraat","streetNumber":"10","postalCode":"2000","floor":2,
            "locality":{"en":"Antwerp"}},"certificate":{"epcCertificate":{"energyLabel":"C",
            "energyValue":212,"certificateNumber":"20260901-0000007890-RES-1"}},
            "heatingType":"gas","renovationObligation":true,"hasTerrace":true,"hasGarden":false,
            "parkingCount":1,"pScore":"A","gScore":"B"}}}
            </script>
        ''', "html.parser"), "https://www.zimmo.be/nl/antwerpen-2000/te-koop/appartement/ZIMMO1")

        normalized = self._normalized(scraper, raw_data)

        self.assertTrue(SHARED_KEYS.issubset(normalized))
        self.assertEqual(normalized["bathrooms"], 1)
        self.assertEqual(normalized["floor"], 2)
        self.assertEqual(normalized["epc_value"], 212)
        self.assertEqual(normalized["epc_certificate_number"], "20260901-0000007890-RES-1")
        self.assertEqual(normalized["heating_type"], "gas")
        self.assertTrue(normalized["renovation_obligation"])
        self.assertTrue(normalized["terrace"])
        self.assertFalse(normalized["garden"])
        self.assertEqual(normalized["parking"], 1)
        self.assertEqual(normalized["p_score"], "A")
        self.assertEqual(normalized["g_score"], "B")
        self.assertIsNone(normalized["agent_name"])


if __name__ == "__main__":
    unittest.main()
