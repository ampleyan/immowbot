# Immowbot Buyer

Immowbot Buyer collects property listings from Immoweb, Immoscoop, and Zimmo, stores them locally, and ranks them against a home search for Antwerp.

The default search covers houses and apartments in postcodes 2000 and 2018, up to €385,000, with at least 80 m², two bedrooms, and EPC A–C.

## Requirements

- Python 3.12
- Google Chrome

## Install

From the project root, create and activate a virtual environment, then install the dependencies.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS or Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If you already have an older virtual environment whose Python executable no longer works, remove and recreate that environment using the commands above.

## Start the dashboard

```bash
python run_dashboard.py
```

Streamlit prints a local URL, normally `http://localhost:8501`. Open it in a browser.

On first launch, Immowbot creates `data/buyer.db` and saves the default `antwerp-home` search. In the dashboard:

1. Select **Run collection** in the sidebar.
2. The dashboard checks for updates every two seconds and adds newly saved listings after every five property checks.
3. Select **Cancel collection** to stop after the current property check. Listings already saved remain available and the run is marked cancelled.
4. Review ranked listings in **Listings**. Each listing includes an image carousel when portal photos are available; use **‹** and **›** to browse them. Select **Detail** for a score breakdown and the original portal link.
5. Use **Run history** to see each collection and the result from every portal.

Listings that do not meet the search’s hard filters are hidden by default; enable **Show excluded listings** to inspect them.

## Run daily collection

Keep the scheduled collector running in a terminal:

```bash
python run_scheduler.py
```

It runs every day at 08:00 local machine time. Each run upserts the `antwerp-home` search, stores the latest observations in `data/buyer.db`, and writes timestamped progress, completion status, and errors to the terminal. Stop it with `Ctrl+C`.

To change the collection time or default search criteria, edit these constants before starting the scheduler:

- `RUN_AT` in `src/buyer/scheduler.py`
- `DEFAULT_HOME_SEARCH` in `src/buyer/search_config.py`

Restart the scheduler after making either change. The updated default search is saved on the next dashboard launch or scheduled collection.

## Run tests

```bash
python -m pytest tests/ -v
```

The suite covers the SQLite store, search validation, scoring, collection behavior, and a full fake-scraper smoke test.

## How ranking works

Every listing must match the configured postcode, type, price ceiling, minimum surface area, bedroom count, and EPC label. Matching listings receive a score out of 100 based on:

- Price headroom: 30 points
- Surface area: 25 points
- Bedrooms: 15 points
- EPC: 20 points
- Data completeness: 10 points

The dashboard sorts matching listings from highest to lowest score.

## Data and privacy

All buyer-assistant data is stored locally in `data/buyer.db`. The database keeps a version history for a listing when its observed details change. Use the scraper responsibly and comply with each portal’s terms of service.

## Legacy analysis CLI

The repository also contains the earlier general-purpose scraping and Excel-analysis workflow. Its entry point remains available:

```bash
python main.py --list-websites
```

The buyer dashboard and scheduler are the recommended workflow for the Antwerp home search.
