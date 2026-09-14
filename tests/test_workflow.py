import os
import tempfile
import unittest

from src.buyer.property_store import PropertyStore


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix='.sqlite3')
        os.close(handle)
        self.store = PropertyStore(self.path)

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_defaults_and_persistence(self):
        self.assertEqual(self.store.get_workflow('immoweb', '1')['status'], 'New')
        saved = self.store.save_workflow('immoweb', '1', {'status': 'Contacted', 'agent_name': 'Alex'})
        self.assertEqual(saved['status'], 'Contacted')
        self.assertEqual(self.store.get_workflow('immoweb', '1')['agent_name'], 'Alex')

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            self.store.save_workflow('immoweb', '1', {'status': 'Unknown'})

    def test_interactions_are_persisted_newest_first(self):
        first = self.store.add_interaction('immoweb', '1', 'call', 'Asked about the viewing')
        second = self.store.add_interaction('immoweb', '1', 'email', 'Sent available times')

        interactions = self.store.get_interactions('immoweb', '1')

        self.assertEqual(interactions[0]['id'], second['id'])
        self.assertEqual(interactions[0]['kind'], 'email')
        self.assertEqual(interactions[1]['note'], 'Asked about the viewing')
        self.assertIsNotNone(first['occurred_at'])

    def test_status_change_creates_interaction(self):
        self.store.save_workflow('immoweb', '1', {'status': 'Contacted'})

        interactions = self.store.get_interactions('immoweb', '1')

        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0]['kind'], 'status')
        self.assertIn('Contacted', interactions[0]['note'])

    def test_rejection_reason_is_persisted(self):
        saved = self.store.save_workflow('immoweb', '1', {'status': 'Rejected', 'rejection_reason': 'Too expensive'})

        self.assertEqual(saved['rejection_reason'], 'Too expensive')
        self.assertIn('Too expensive', self.store.get_interactions('immoweb', '1')[0]['note'])


if __name__ == '__main__':
    unittest.main()
