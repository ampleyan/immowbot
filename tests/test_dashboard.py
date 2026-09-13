import os
import tempfile
import threading
import unittest

from src.buyer import dashboard


class DashboardStoreTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        self.original_path = dashboard.DB_PATH
        dashboard.DB_PATH = self.path
        getattr(dashboard.get_store, "clear", lambda: None)()

    def tearDown(self):
        getattr(dashboard.get_store, "clear", lambda: None)()
        dashboard.DB_PATH = self.original_path
        os.unlink(self.path)

    def test_store_is_usable_from_a_later_streamlit_thread(self):
        main_store = dashboard.get_store()
        errors = []

        def use_store():
            try:
                worker_store = dashboard.get_store()
                worker_store.list_searches()
                worker_store.close()
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=use_store)
        worker.start()
        worker.join()
        main_store.close()

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
