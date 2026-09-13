import unittest

from src.buyer.commute import commute_estimate


class CommuteTest(unittest.TestCase):
    def test_coordinates_produce_distance_and_score(self):
        result = commute_estimate({"latitude": 51.22, "longitude": 4.4}, [{"name": "Work", "latitude": 51.22, "longitude": 4.4, "mode": "driving", "max_minutes": 30}])
        self.assertTrue(result["available"])
        self.assertEqual(result["destinations"][0]["minutes"], 0)
        self.assertEqual(result["score"], 100)

    def test_missing_coordinates_are_unavailable(self):
        self.assertFalse(commute_estimate({}, [{"name": "Work", "latitude": 1, "longitude": 1}])["available"])


if __name__ == '__main__':
    unittest.main()
