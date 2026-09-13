import os
import tempfile
import unittest

from src.buyer.property_store import PropertyStore


class AlertsTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix='.sqlite3')
        os.close(handle)
        self.store = PropertyStore(self.path)

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_alerts_are_deduplicated_and_markable(self):
        self.store.add_alert('immoweb', '1', 'price_reduction', 'Price reduced', 'https://x')
        self.store.add_alert('immoweb', '1', 'price_reduction', 'Price reduced', 'https://x')
        alerts = self.store.get_alerts()
        self.assertEqual(len(alerts), 1)
        self.store.mark_alert_read(alerts[0]['id'])
        self.assertIsNotNone(self.store.get_alerts()[0]['read_at'])


if __name__ == '__main__':
    unittest.main()
