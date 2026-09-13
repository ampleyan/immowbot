import unittest

from src.buyer.property_explanation import explain_property


class ExplanationTest(unittest.TestCase):
    def test_excluded_explanation_is_explicit(self):
        result = explain_property({}, None, {}, ["hard_filters"], None)
        self.assertIn("hard_filters", result["summary"])

    def test_affordability_and_contributors_are_deterministic(self):
        result = explain_property({}, 82, {"price": 28, "surface_area": 20, "bedrooms": 3}, [], {"available": True, "cash_surplus": 5000})
        self.assertIn("affordable", result["summary"])
        self.assertIn("price", result["summary"])
        self.assertEqual(result, explain_property({}, 82, {"price": 28, "surface_area": 20, "bedrooms": 3}, [], {"available": True, "cash_surplus": 5000}))


if __name__ == "__main__":
    unittest.main()
