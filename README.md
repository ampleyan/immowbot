# Immowbot - Belgian Property Market Analysis Tool

Immowbot is a Python-based tool for scraping and analyzing property data from Immoweb.be to help with property market research in Belgium.

## Features

- **Web Scraping**: Automated extraction of property listings from Immoweb.be
- **Data Analysis**: Comprehensive analysis of prices, locations, EPC scores, and property characteristics
- **Export Options**: Excel reports with multiple sheets and CSV exports
- **Visualizations**: Charts and graphs showing market trends and distributions
- **Filtering**: Support for price, surface area, EPC score, and location filters

## Installation

1. Clone or download this repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

```bash
# Scrape with filters
python main.py --max-price 230000 --min-surface 80 --epc-scores "A++,A+,A,B" --pages 5

# Filter by specific postal codes (Antwerp area)
python main.py --postal-codes "2060,2050,2140,2020,2018,2000" --max-price 230000 --pages 3
postalCodes=
# Combine all filters
python main.py --max-price 230000 --min-surface 80 --epc-scores "A++,A+,A,B" --postal-codes "BE-2060,BE-2050,BE-2140,BE-2020,BE-2018,BE-2000" --pages 5

# Scrape from a specific search URL
python main.py --search-url "https://www.immoweb.be/en/search/house-and-apartment/for-sale?countries=BE&epcScores=A++,A,B,A+&maxPrice=230000&minSurface=80&postalCodes=BE-2060,BE-2050,BE-2140,BE-2020,BE-2018,BE-2000&page=1&orderBy=relevance" --pages 3

# Export to custom filename
python main.py --max-price 200000 --output "my_analysis.xlsx"
```

### Command Line Options

- `--search-url`: Direct Immoweb search URL to scrape
- `--max-price`: Maximum property price filter
- `--min-surface`: Minimum surface area filter (m²)
- `--epc-scores`: EPC energy scores to include (comma-separated)
- `--postal-codes`: Postal codes to filter by (comma-separated, e.g. "2060,2050" or "BE-2060,BE-2050")
- `--output`: Output filename (default: property_analysis.xlsx)
- `--pages`: Number of search result pages to scrape (default: 5)

## Output

The tool generates:

1. **Excel Report** with multiple sheets:
   - Raw Data: All scraped property information
   - Summary: Key statistics and insights
   - Price Analysis: Price distributions and ranges
   - Location Analysis: Properties and prices by location
   - Postcode Analysis: Properties and prices by postal code
   - EPC Analysis: Energy efficiency score breakdown

2. **Visualization Charts**: Graphs showing price distributions, EPC scores, and market trends

## Data Fields Extracted

For each property:
- Price
- Location and postcode
- Surface area (m²)
- EPC energy score
- Property type (house/apartment)
- Number of bedrooms
- Construction year
- Property URL for reference

## Troubleshooting

If you encounter issues:

1. **WebDriver errors**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for Chrome driver fixes
2. **HTTP 403 errors**: Website may be blocking requests - try using a VPN or manual data entry
3. **No properties found**: Try broader filters or manual verification on immoweb.be
4. **Manual backup**: Run `python manual_data_input.py` to enter property data manually

## Alternative Usage

If automated scraping fails, you can still analyze properties:

```bash
# Manual data entry tool
python manual_data_input.py

# Simple test script
python test_scraper.py

# Ready-to-use analysis script
python run_analysis.py
```

## Legal Notice

This tool is for personal research and educational purposes only. Please respect Immoweb.be's terms of service and use reasonable delays between requests. The tool includes built-in delays to be respectful of the website's resources.

## Requirements

- Python 3.12+
- Chrome browser (for Selenium WebDriver)
- All packages listed in requirements.txt