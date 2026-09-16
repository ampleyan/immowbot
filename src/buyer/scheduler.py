import logging
import os
import sys
import time

import schedule

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.buyer.collector import run_collection
from src.buyer.database import load_database_settings
from src.buyer.property_store import PropertyStore
from src.buyer.search_config import DEFAULT_HOME_SEARCH
from src.scraper_manager import ScraperManager

SEARCH_NAME = "antwerp-home"
RUN_AT = "08:00"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def job():
    logging.info("Starting scheduled collection")
    settings = load_database_settings()
    store = PropertyStore(settings.dsn)
    try:
        user = store.get_user_by_username("ampleyan")
        if not user:
            logging.error("User 'ampleyan' not found — skipping collection")
            return
        user_id = user["id"]
        search_id = store.save_search(user_id, SEARCH_NAME, "home", DEFAULT_HOME_SEARCH)
        manager = ScraperManager()
        run_id = run_collection(store, search_id, manager)
        run = store.get_run(run_id)
        logging.info("Run %d complete — status: %s", run_id, run["status"])
    except Exception:
        logging.exception("Collection failed")
    finally:
        store.close()


def main():
    schedule.every().day.at(RUN_AT).do(job)
    logging.info("Scheduler started — daily run at %s. Press Ctrl-C to stop.", RUN_AT)
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
