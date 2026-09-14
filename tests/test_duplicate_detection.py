import unittest

from src.buyer.duplicate_detection import duplicate_groups


class DuplicateDetectionTest(unittest.TestCase):
    def test_same_address_groups_offers(self):
        listings = [
            {"source": "immoweb", "source_listing_id": "1", "address": "Main 1, 2000 Antwerp", "postcode": "2000", "price": 300000, "surface_area": 100},
            {"source": "zimmo", "source_listing_id": "2", "address": "Main 1, 2000 Antwerp", "postcode": "2000", "price": 300000, "surface_area": 102},
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

    def test_same_price_and_surface_without_identity_do_not_group(self):
        listings = [
            {"source": "immoweb", "source_listing_id": "1", "price": 300000, "surface_area": 100},
            {"source": "zimmo", "source_listing_id": "2", "price": 300000, "surface_area": 102},
        ]
        self.assertEqual(duplicate_groups(listings), [])

    def test_identity_requires_matching_postcode(self):
        listings = [
            {"source": "immoweb", "source_listing_id": "1", "address": "Main 1", "postcode": "2000", "price": 300000, "surface_area": 100},
            {"source": "zimmo", "source_listing_id": "2", "address": "Main 1", "postcode": "2018", "price": 300000, "surface_area": 100},
        ]
        self.assertEqual(duplicate_groups(listings), [])

    def test_matching_identity_and_details_are_high_confidence(self):
        listings = [
            {"source": "immoweb", "source_listing_id": "1", "address": "Main 1", "postcode": "2000", "price": 300000, "surface_area": 100, "bedrooms": 3},
            {"source": "zimmo", "source_listing_id": "2", "address": "Main 1", "postcode": "2000", "price": 300000, "surface_area": 102, "bedrooms": 3},
        ]
        groups = duplicate_groups(listings)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["confidence"], "high")
        self.assertEqual(groups[0]["signals"][0]["signals"], ["address", "postcode", "price", "surface", "bedrooms"])


if __name__ == '__main__':
    unittest.main()
