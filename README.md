# Immowbot - Belgian Property Market Analysis Tool

Immowbot is a Python-based tool for scraping and analyzing property data from Immoweb.be to help with property market research in Belgium.

## Features

- **Web Scraping**: Automated extraction of property listings from Immoweb.be
- **Data Analysis**: Comprehensive analysis of prices, locations, EPC scores, and property characteristics
- **JSON Analysis**: Analyze existing property data from JSON files without re-scraping
- **Travel Time Calculation**: Calculate commute times to reference locations using different transport modes
- **Export Options**: Excel reports with multiple sheets and CSV exports
- **Duplicate Detection**: Avoid re-scraping already processed properties
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

**Scraping Mode:**
```bash
# Scrape with filters
python main.py --max-price 230000 --min-surface 80 --epc-scores "A++,A+,A,B" --pages 5

# Filter by specific postal codes (Antwerp area)
python main.py --postal-codes "2060,2050,2140,2020,2018,2000" --max-price 230000 --pages 3

# Combine all filters
python main.py --max-price 230000 --min-surface 80 --epc-scores "A++,A+,A,B" --postal-codes "BE-2060,BE-2050,BE-2140,BE-2020,BE-2018,BE-2000" --pages 5

# Scrape from a specific search URL
python main.py --search-url "https://www.immoweb.be/en/search/house-and-apartment/for-sale" --pages 3

# Export to custom filename
python main.py --max-price 200000 --output "my_analysis.xlsx"
```

**JSON Analysis Mode:**
```bash
# Analyze existing JSON data (recommended approach)
python main.py --from-json properties_20250110_143022.json

# Interactive JSON analyzer (easiest to use)
python analyze_json.py --interactive

# Direct JSON analysis
python analyze_json.py my_properties.json

# List available JSON files
python analyze_json.py --list
```

### Command Line Options

**Main Script (main.py):**
- `--from-json`: Analyze properties from existing JSON file instead of scraping
- `--search-url`: Direct Immoweb search URL to scrape
- `--max-price`: Maximum property price filter
- `--min-surface`: Minimum surface area filter (m²)
- `--epc-scores`: EPC energy scores to include (comma-separated)
- `--postal-codes`: Postal codes to filter by (comma-separated, e.g. "2060,2050" or "BE-2060,BE-2050")
- `--output`: Output filename (default: property_analysis.xlsx)
- `--pages`: Number of search result pages to scrape (default: 5)

**JSON Analyzer (analyze_json.py):**
- `json_file`: JSON file to analyze (positional argument)
- `--output`: Output Excel filename
- `--list`: List available JSON files in current directory
- `--interactive`: Run in interactive mode with file selection

## Output

The tool generates:

1. **Excel Report** with multiple sheets:
   - **Property Tracking**: Custom tracking sheet with travel times to reference location
   - **Raw Data**: All scraped property information
   - **Summary**: Key statistics and insights
   - **Price Analysis**: Price distributions and ranges
   - **Location Analysis**: Properties and prices by location
   - **Postcode Analysis**: Properties and prices by postal code
   - **EPC Analysis**: Energy efficiency score breakdown
   - **Feature Analysis**: Building states, amenities, and property features
   - **Geographic Analysis**: Province and city-level insights
   - **Market Segments**: Price segment analysis

2. **JSON Data Files**: Timestamped JSON files with all scraped data for future analysis

3. **Visualization Charts**: Graphs showing price distributions, EPC scores, and market trends

### Travel Time Features

The Property Tracking sheet includes:
- **Car/Bike/Walk Times**: Commute duration to Kronenburgstraat 26
- **Distance Information**: Route distances for each transport mode
- **Automatic Geocoding**: Address-to-coordinate conversion for routing

## Data Fields Extracted

**Core Property Data:**
- Price and price per m²
- Location, postcode, and coordinates
- Surface area and outdoor surface
- EPC energy score and energy type
- Property type (house/apartment)
- Number of bedrooms and construction year
- Building state and kitchen type
- Amenities (terrace, parking)

**Contact Information:**
- Real estate agent details
- Phone, mobile, email, and website
- Agency information

**Travel Data (calculated):**
- Travel times by car, bike, and walking
- Distance information for each mode
- Routes to reference location (Kronenburgstraat 26)

## Troubleshooting

If you encounter issues:

1. **WebDriver errors**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for Chrome driver fixes
2. **HTTP 403 errors**: Website may be blocking requests - try using a VPN or manual data entry
3. **No properties found**: Try broader filters or manual verification on immoweb.be
4. **Manual backup**: Run `python manual_data_input.py` to enter property data manually

## Alternative Usage

**When scraping fails or for re-analysis:**

```bash
# Analyze existing JSON data (fastest)
python analyze_json.py --interactive

# Manual data entry tool
python manual_data_input.py

# Load from specific JSON backup
python analyze_json.py properties_backup.json --output custom_analysis.xlsx
```

**Workflow Recommendation:**
1. **First run**: Use `main.py` to scrape and generate JSON data
2. **Re-analysis**: Use `analyze_json.py` to analyze existing data with updated features
3. **Manual backup**: Use `manual_data_input.py` if scraping fails completely

## Legal Notice

This tool is for personal research and educational purposes only. Please respect Immoweb.be's terms of service and use reasonable delays between requests. The tool includes built-in delays to be respectful of the website's resources.

## Requirements

- Python 3.12+
- Chrome browser (for Selenium WebDriver)
- All packages listed in requirements.txt