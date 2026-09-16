import unittest

from src.buyer.property_store import PropertyStore
from tests.postgres_support import PostgresDatabaseTestCase


class AlertsTest(PostgresDatabaseTestCase):
    user_id = 1

    def setUp(self):
        super().setUp()
        self.store = PropertyStore(self.runtime_dsn)

    def tearDown(self):
        self.store.close()

    def test_alerts_are_deduplicated_and_markable(self):
        self.store.add_alert(self.user_id, 'immoweb', '1', 'price_reduction', 'Price reduced', 'https://x')
        self.store.add_alert(self.user_id, 'immoweb', '1', 'price_reduction', 'Price reduced', 'https://x')
        alerts = self.store.get_alerts(self.user_id)
        self.assertEqual(len(alerts), 1)
        self.store.mark_alert_read(self.user_id, alerts[0]['id'])
        self.assertIsNotNone(self.store.get_alerts(self.user_id)[0]['read_at'])

    def test_clear_alerts_deletes_all_alerts(self):
        self.store.add_alert(self.user_id, 'immoweb', '1', 'price_reduction', 'Price reduced', 'https://x')
        self.store.add_alert(self.user_id, 'zimmo', '2', 'photos_added', 'New photos added', 'https://y')
        alerts = self.store.get_alerts(self.user_id)
        self.store.mark_alert_read(self.user_id, alerts[-1]['id'])
        self.store.clear_alerts(self.user_id)
        self.assertEqual(self.store.get_alerts(self.user_id), [])

    def test_alert_id_is_integer(self):
        self.store.add_alert(self.user_id, 'immoweb', '1', 'price_reduction', 'Price reduced', 'https://x')
        alerts = self.store.get_alerts(self.user_id)
        self.assertIsInstance(alerts[0]['id'], int)

    def test_alert_created_at_is_string(self):
        self.store.add_alert(self.user_id, 'immoweb', '1', 'price_reduction', 'Price reduced', 'https://x')
        alerts = self.store.get_alerts(self.user_id)
        self.assertIsInstance(alerts[0]['created_at'], str)
        self.assertIn('T', alerts[0]['created_at'])


if __name__ == '__main__':
    unittest.main()
