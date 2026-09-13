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


if __name__ == '__main__':
    unittest.main()
