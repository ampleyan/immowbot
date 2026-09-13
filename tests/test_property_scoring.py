import unittest

from src.buyer.property_scoring import calculate_home_score, calculate_investment_score, passes_hard_filters
from src.buyer.search_config import DEFAULT_HOME_SEARCH


class PropertyScoringTest(unittest.TestCase):
    def setUp(self):
        self.sale = {
            "postcode": "2018",
            "property_type": "apartment",
            "price": 300000,
            "surface_area": 100,
            "bedrooms": 2,
            "epc_score": "B",
            "url": "https://example.test/sale",
        }
        self.rentals = [
            {"postcode": "2018", "property_type": "apartment", "surface_area": 95, "bedrooms": 2, "price": 1200},
            {"postcode": "2018", "property_type": "apartment", "surface_area": 105, "bedrooms": 3, "price": 1300},
            {"postcode": "2000", "property_type": "house", "surface_area": 100, "bedrooms": 2, "price": 2200},
        ]

    def test_hard_filters_reject_missing_or_unaccepted_epc(self):
        self.assertFalse(passes_hard_filters({**self.sale, "epc_score": None}, DEFAULT_HOME_SEARCH))
        self.assertFalse(passes_hard_filters({**self.sale, "epc_score": "D"}, DEFAULT_HOME_SEARCH))

    def test_home_score_is_bounded_and_explained(self):
        result = calculate_home_score(self.sale, DEFAULT_HOME_SEARCH)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertEqual(set(result["components"]), {"price", "surface_area", "bedrooms", "epc", "completeness"})

    def test_investment_score_exposes_comparable_evidence(self):
        result = calculate_investment_score(self.sale, DEFAULT_HOME_SEARCH, self.rentals)
        self.assertEqual(result["components"]["comparable_count"], 2)
        self.assertEqual(result["components"]["median_monthly_rent"], 1250)
        self.assertEqual(result["components"]["gross_yield_percent"], 5.0)

    def test_missing_comparables_do_not_fabricate_yield(self):
        result = calculate_investment_score(self.sale, DEFAULT_HOME_SEARCH, [])
        self.assertIsNone(result["components"]["median_monthly_rent"])
        self.assertIsNone(result["components"]["gross_yield_percent"])


if __name__ == "__main__":
    unittest.main()
