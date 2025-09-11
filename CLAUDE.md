# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Immowbot is a Python 3.12 property market analysis tool that scrapes Belgian real estate data from Immoweb.be. It provides comprehensive market analysis including price distributions, location comparisons, EPC energy scores, and property characteristics.

## Project Structure

```
immowbot/
├── main.py                 # Main entry point and CLI interface
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── src/
│   ├── __init__.py
│   ├── scraper.py         # Immoweb.be web scraper using Selenium
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

# Run basic property analysis
python main.py --max-price 230000 --min-surface 80 --epc-scores "A++,A+,A,B" --pages 5

# Filter by postal codes (Antwerp area)
python main.py --postal-codes "2060,2050,2140,2020,2018,2000" --max-price 230000 --pages 3

# Combine all filters with geolocation analysis
python main.py --max-price 230000 --min-surface 80 --epc-scores "A++,A+,A,B" --postal-codes "BE-2060,BE-2050" --pages 5 --enable-geo-analysis

# Scrape from specific search URL with speed mode
python main.py --search-url "https://www.immoweb.be/en/search/..." --pages 3 --llm-speed-mode

# Disable LLM analysis for faster processing
python main.py --max-price 230000 --pages 5 --disable-llm

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