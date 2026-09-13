import unittest

from src.buyer.change_tracking import diff_versions


class ChangeTrackingTest(unittest.TestCase):
    def test_price_reduction_and_added_photos(self):
        changes = diff_versions({"price": 300000, "images": ["a"]}, {"price": 285000, "images": ["a", "b"]})
        self.assertEqual(changes[0]["change_type"], "price_reduction")
        self.assertEqual(changes[1]["change_type"], "photos_added")

    def test_identical_payload_has_no_changes(self):
        payload = {"price": 300000, "epc_score": "B"}
        self.assertEqual(diff_versions(payload, payload), [])


if __name__ == "__main__":
    unittest.main()
