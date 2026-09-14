# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

Immowbot is a Python 3.12 property market analysis tool that scrapes Belgian real estate data from multiple Belgian websites including Immoweb.be, Immoscoop.be, and Zimmo.be. It provides comprehensive market analysis including price distributions, location comparisons, EPC energy scores, and property characteristics with LLM-powered description analysis.

## Project Structure

```
immowbot/
├── main.py                 # Main entry point and CLI interface
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── src/
│   ├── __init__.py
│   ├── base_scraper.py    # Base scraper interface
│   ├── scraper_manager.py # Multi-scraper coordination
│   ├── scrapers/          # Website-specific scrapers
│   │   ├── immoweb_scraper.py    # Immoweb.be scraper
│   │   ├── immoscoop_scraper.py  # Immoscoop.be scraper
│   │   └── zimmo_scraper.py      # Zimmo.be scraper
│   ├── llm_analyzer.py    # Local LLM description analysis
│   ├── analyzer.py        # Property data analysis and statistics
│   └── exporter.py        # Excel/CSV export and visualization
└── .venv/                 # Virtual environment
```

## Development Environment

- Python version: 3.12
- Virtual environment: `.venv`
- Web scraping: Selenium WebDriver with Chrome
- Data analysis: pandas, numpy, matplotlib, seaborn
- Export formats: Excel (openpyxl), CSV
- Code formatter: Black (configured in IDE)

## Common Commands

```bash
# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Unix/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# List available websites
python main.py --list-websites

# Run basic property analysis (Immoweb by default)
python main.py --max-price 230000 --min-surface 80 --epc-scores "A++,A+,A,B" --pages 5

# Scrape specific website
python main.py --website immoscoop --max-price 230000 --pages 3

# Scrape multiple websites
python main.py --websites immoweb immoscoop zimmo --max-price 230000 --pages 2

# Scrape all available websites
python main.py --website all --max-price 230000 --pages 2

# Filter by postal codes (Antwerp area) with geolocation analysis
python main.py --postal-codes "2060,2050,2140,2020,2018,2000" --max-price 230000 --pages 3 --enable-geo-analysis

# Combine all filters with LLM speed mode
python main.py --website immoweb --max-price 230000 --min-surface 80 --epc-scores "A++,A+,A,B" --postal-codes "BE-2060,BE-2050" --pages 5 --llm-speed-mode

# Scrape from specific search URL (auto-detects website)
python main.py --search-url "https://www.immoweb.be/en/search/..." --pages 3

# Multi-website scraping with no LLM for fastest processing
python main.py --websites immoweb immoscoop --max-price 230000 --pages 3 --disable-llm

# Exclude properties with current tenants (owner-occupied only)
python main.py --max-price 230000 --pages 5 --exclude-tenants

# Format code with Black
black .
```

## Key Components

1. **ImmowebScraper** (`src/scraper.py`): Handles web scraping with Selenium, extracts property details including price, location, EPC score, surface area, and other characteristics

2. **PropertyAnalyzer** (`src/analyzer.py`): Analyzes scraped data to generate statistics, price distributions, location comparisons, and market insights

3. **DataExporter** (`src/exporter.py`): Exports analysis results to Excel with multiple sheets and creates visualization charts

## Data Fields Extracted

- Price and price per m²
- Location and postcode  
- Surface area (m²)
- EPC energy efficiency score
- Property type (house/apartment)
- Number of bedrooms
- Construction year
- Property URL

## Technical Notes

- Uses Selenium with headless Chrome for robust web scraping
- Implements respectful scraping with delays between requests
- Handles data cleaning and type conversion for analysis
- Generates comprehensive Excel reports with multiple analysis sheets
- Creates matplotlib visualizations for market trends