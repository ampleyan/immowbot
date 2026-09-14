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

    def test_hard_filters_respect_postcode_and_new_search_preferences(self):
        config = {**DEFAULT_HOME_SEARCH, "outdoor_features": ["terrace", "garden"], "min_construction_year": 2010}
        listing = {**self.sale, "outdoor_terrace": True, "outdoor_garden": True, "construction_year": 2015}
        self.assertTrue(passes_hard_filters(listing, config))
        self.assertFalse(passes_hard_filters({**listing, "postcode": "9999"}, config))
        self.assertFalse(passes_hard_filters({**listing, "construction_year": 2005}, config))
        self.assertFalse(passes_hard_filters({**listing, "outdoor_garden": False}, config))

    def test_home_score_is_bounded_and_explained(self):
        result = calculate_home_score(self.sale, DEFAULT_HOME_SEARCH)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertEqual(set(result["components"]), {"price", "surface_area", "bedrooms", "epc", "completeness", "outdoor"})

    def test_home_score_uses_configured_weights(self):
        config = {**DEFAULT_HOME_SEARCH, "score_weights": {"price": 100, "surface_area": 0, "bedrooms": 0, "epc": 0, "completeness": 0}}
        result = calculate_home_score(self.sale, config)
        self.assertEqual(result["score"], result["components"]["price"])

    def test_outdoor_features_add_a_score_bonus(self):
        without_outdoor = calculate_home_score(self.sale, DEFAULT_HOME_SEARCH)
        with_terrace = calculate_home_score({**self.sale, "outdoor_terrace": True}, DEFAULT_HOME_SEARCH)
        with_garden = calculate_home_score({**self.sale, "outdoor_garden": True}, DEFAULT_HOME_SEARCH)

        self.assertEqual(with_terrace["components"]["outdoor"], 5)
        self.assertEqual(with_garden["components"]["outdoor"], 5)
        self.assertEqual(with_terrace["score"], without_outdoor["score"] + 5)

    def test_surface_above_minimum_scores_as_strong(self):
        config = {**DEFAULT_HOME_SEARCH, "min_surface_area": 85}
        result = calculate_home_score({**self.sale, "surface_area": 109}, config)
        self.assertEqual(result["components"]["surface_area"], 25)

    def test_epc_b_is_scored_as_strong_but_below_a(self):
        b_score = calculate_home_score(self.sale, DEFAULT_HOME_SEARCH)["components"]["epc"]
        a_score = calculate_home_score({**self.sale, "epc_score": "A"}, DEFAULT_HOME_SEARCH)["components"]["epc"]
        self.assertEqual(b_score, 17)
        self.assertLess(b_score, a_score)

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
