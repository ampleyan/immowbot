import logging
import sys
import time

import schedule

from src.buyer.collector import run_collection
from src.buyer.property_store import PropertyStore
from src.buyer.search_config import DEFAULT_HOME_SEARCH

DB_PATH = "data/buyer.db"
SEARCH_NAME = "antwerp-home"
RUN_AT = "08:00"


def run_scheduled_collection():
    store = None
    try:
        from src.scraper_manager import ScraperManager

        store = PropertyStore(DB_PATH)
        search_id = store.save_search(SEARCH_NAME, "home", DEFAULT_HOME_SEARCH)
        logging.info("Collection started")
        run_id = run_collection(store, search_id, ScraperManager())
        status = store.get_run(run_id)["status"]
        logging.info("Collection run %s completed with status %s", run_id, status)
    except Exception:
        logging.exception("Collection run failed")
    finally:
        if store is not None:
            store.close()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    schedule.every().day.at(RUN_AT).do(run_scheduled_collection)
    logging.info("Daily collection scheduled for %s", RUN_AT)
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
