import unittest
from datetime import datetime, timezone

from src.buyer.smart_lists import BUILTIN_SMART_LISTS, explain_rule_match, matches_rule


class SmartListRuleTest(unittest.TestCase):
    def setUp(self):
        self.listing = {
            "source": "immoweb", "postcode": "2000", "property_type": "apartment",
            "outdoor_terrace": True, "_first_seen_at": "2026-09-10T00:00:00+00:00",
        }
        self.now = datetime(2026, 9, 13, tzinfo=timezone.utc)

    def test_builtin_rules_cover_required_views(self):
        self.assertEqual({name for name, _ in BUILTIN_SMART_LISTS}, {"Contact now", "Affordable", "Cash shortfall", "New this week", "Terrace or garden", "Needs review", "By postcode", "By portal"})

    def test_score_and_affordability(self):
        purchase = {"available": True, "cash_surplus": 1000}
        self.assertTrue(matches_rule(self.listing, {"score_min": 75, "affordability": "affordable"}, 80, purchase, self.now))
        self.assertFalse(matches_rule(self.listing, {"score_min": 75}, 70, purchase, self.now))

    def test_age_and_outdoor_rules(self):
        self.assertTrue(matches_rule(self.listing, {"first_seen_days": 7}, 50, None, self.now))
        self.assertTrue(matches_rule(self.listing, {"outdoor_features": ["garden", "terrace"]}, 50, None, self.now))
        self.assertFalse(matches_rule({**self.listing, "outdoor_terrace": False}, {"outdoor_features": ["terrace"]}, 50, None, self.now))

    def test_needs_review_accepts_missing_finance_or_low_score(self):
        self.assertTrue(matches_rule(self.listing, {"needs_review": True}, None, None, self.now))
        self.assertTrue(matches_rule(self.listing, {"needs_review": True}, 40, {"available": True, "cash_surplus": 1000}, self.now))

    def test_explanations_identify_contact_now_reasons(self):
        reason = explain_rule_match(self.listing, {"score_min": 75, "affordability": "affordable"}, 80, {"available": True, "cash_surplus": 1000})
        self.assertIn("score 80/100", reason)
        self.assertIn("purchase estimate is affordable", reason)

    def test_explanations_identify_needs_review_reasons(self):
        reason = explain_rule_match(self.listing, {"needs_review": True}, 40, {"available": True, "cash_surplus": 1000})
        self.assertIn("score is below the review threshold", reason)


if __name__ == "__main__":
    unittest.main()
