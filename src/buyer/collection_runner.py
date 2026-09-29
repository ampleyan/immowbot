import json
import os
import queue
import threading
import time
from datetime import datetime, timezone

from src.buyer.property_store import PropertyStore
from src.scraper_manager import ScraperManager


BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "backups"))


def _save_listings_backup(store, run_id):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    listings = store.latest_listings("sale")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(BACKUP_DIR, f"{timestamp}_run-{run_id}.json")
    with open(path, "w", encoding="utf-8") as backup_file:
        json.dump(listings, backup_file, ensure_ascii=False, indent=2, default=str)


def start_collection_worker(state, store_dsn, search_id, selected_listings=None):
    """Start one full or selected collection with shared run lifecycle handling."""
    cancel_event = threading.Event()
    progress_queue = queue.Queue()
    selected_count = len(selected_listings) if selected_listings is not None else 0

    def worker(store_dsn, search_id, selected, cancel, progress):
        from src.buyer.collector import run_collection, run_selected_collection

        store = PropertyStore(store_dsn)
        manager = ScraperManager()

        def on_translate(done, total, current):
            if done >= total:
                state["translation"] = None
            else:
                state["translation"] = {"total": total, "done": done, "current": current}

        try:
            if selected is None:
                run_id = run_collection(
                    store,
                    search_id,
                    manager,
                    on_progress=progress.put,
                    should_cancel=cancel.is_set,
                    on_translate_progress=on_translate,
                )
            else:
                run_id = run_selected_collection(
                    store,
                    search_id,
                    manager,
                    selected,
                    on_progress=progress.put,
                    should_cancel=cancel.is_set,
                    on_translate_progress=on_translate,
                )
            progress.put({"status": store.get_run(run_id)["status"]})
            _save_listings_backup(store, run_id)
        except Exception as exc:
            progress.put({"status": "error", "error": str(exc)})
        finally:
            state["translation"] = None
            store.close()

    thread = threading.Thread(
        target=worker,
        args=(store_dsn, search_id, selected_listings, cancel_event, progress_queue),
        daemon=True,
    )
    state["collection"] = {
        "thread": thread,
        "cancel_event": cancel_event,
        "progress_queue": progress_queue,
        "selected": selected_count,
        "started_at": time.time(),
        "progress": {"checked": 0, "saved": 0, "failed": 0, "status": "running", "phase": "starting"},
    }
    thread.start()
