import unittest

from src.buyer.duplicate_detection import duplicate_groups


class DuplicateDetectionTest(unittest.TestCase):
    def test_same_address_groups_offers(self):
        listings = [
            {"source": "immoweb", "source_listing_id": "1", "address": "Main 1, 2000 Antwerp", "price": 300000},
            {"source": "zimmo", "source_listing_id": "2", "address": "Main 1, 2000 Antwerp", "price": 305000},
        ]
        groups = duplicate_groups(listings)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["confidence"], "high")

    def test_unique_listings_not_grouped(self):
        self.assertEqual(duplicate_groups([{ "source": "immoweb", "source_listing_id": "1", "address": "A" }]), [])

    def test_dimensions_alone_do_not_create_duplicate_group(self):
        listings = [
            {"source": "immoweb", "source_listing_id": "1", "surface_area": 100, "bedrooms": 3},
            {"source": "zimmo", "source_listing_id": "2", "surface_area": 100, "bedrooms": 3},
        ]
        self.assertEqual(duplicate_groups(listings), [])

    def test_same_price_and_surface_can_create_candidate_group(self):
        listings = [
            {"source": "immoweb", "source_listing_id": "1", "price": 300000, "surface_area": 100},
            {"source": "zimmo", "source_listing_id": "2", "price": 300000, "surface_area": 102},
        ]
        groups = duplicate_groups(listings)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["confidence"], "medium")
        self.assertEqual(groups[0]["signals"][0]["signals"], ["price", "surface"])


if __name__ == '__main__':
    unittest.main()
