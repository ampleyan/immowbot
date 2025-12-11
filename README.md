# Immowbot - Belgian Property Market Analysis Tool

Immowbot is a Python-based tool for scraping and analyzing property data from multiple Belgian real estate websites to help with property market research in Belgium.

## Features

- **Multi-Website Scraping**: Automated extraction from multiple Belgian real estate platforms:
  - **Immoweb.be**: Belgium's largest real estate platform
  - **Immoscoop.be**: Belgian real estate with exclusive listings  
  - **Zimmo.be**: Belgian real estate platform
- **LLM Analysis**: Local Ollama integration for property description analysis and insights
- **Data Analysis**: Comprehensive analysis of prices, locations, EPC scores, and property characteristics
- **JSON Analysis**: Analyze existing property data from JSON files without re-scraping
- **Geolocation Analysis**: Optional travel time calculation to reference locations (disabled by default)
- **Organized File Structure**: Automatic organization of scraping and analysis results into separate folders
- **Source-Specific Excel Sheets**: Separate analysis sheets for each website (Immoweb, Immoscoop, Zimmo)
- **Export Options**: Clean Excel reports with source-separated data
- **Duplicate Detection**: Avoid re-scraping already processed properties
- **Advanced Filtering**: Support for price, surface area, EPC score, and location filters across all websites

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

## File Organization

Immowbot automatically organizes all files into a clean folder structure:

```
immowbot/
├── scraping_results/           # Raw scraping data
│   ├── immoweb_properties_20250912_172812.json
│   ├── immoscoop_properties_20250911_190815.json
│   └── zimmo_properties_20250910_143022.json
├── analysis_results/           # Analysis outputs  
│   ├── property_analysis.xlsx  # Excel with source-specific sheets
│   └── property_analysis_analyses.json  # Detailed analysis data
├── src/                       # Source code
├── main.py                    # Main scraper
└── analyze_json.py           # JSON analyzer
```

**Benefits:**
- 📁 **Clean workspace**: No more scattered files in root directory
- 🔍 **Easy navigation**: Find what you need quickly
- 🌐 **Source separation**: Each website gets its own data organization
- 📊 **Analysis ready**: All outputs organized for easy access

## Usage

### Basic Usage

**Single Website Scraping:**
```bash
# Scrape Immoweb (default website)
python main.py --max-price 370000 --min-surface 80 --epc-scores "A++,A+,A,B,C" --postal-codes "2000,2018,2060,2140" --pages 1

# Scrape Immoscoop
python main.py --website immoscoop --max-price 230000 --postal-codes "2060,2050" --pages 3

# Scrape Zimmo
python main.py --website zimmo --min-surface 80 --pages 3

# Scrape from specific URL (website auto-detected)
python main.py --search-url "https://www.immoweb.be/en/search/house-and-apartment/for-sale" --pages 3
```

**Multi-Website Scraping:**
```bash
# Scrape multiple specific websites
python main.py --websites immoweb immoscoop --max-price 230000 --pages 3

# Scrape all available websites
python main.py --website all --max-price 320000  --pages 2

# List available websites
python main.py --list-websites
```

**Advanced Options:**
```bash
# Combine filters across websites
python main.py --website all --max-price 230000 --min-surface 80 --epc-scores "A++,A+,A,B" --postal-codes "2060,2050,2140" --pages 3

# Enable geolocation analysis and LLM analysis
python main.py --website immoweb --max-price 200000 --enable-geo-analysis --pages 3

# Disable LLM analysis for faster processing
python main.py --website immoscoop --max-price 200000 --disable-llm --pages 3

# Use LLM speed mode for faster analysis
python main.py --website zimmo --max-price 200000 --llm-speed-mode --pages 3

# Custom output filename (saves to analysis_results/ folder)
python main.py --websites immoweb immoscoop --max-price 200000 --output "multi_site_analysis.xlsx"
```

**JSON Analysis Mode:**
```bash
# Analyze existing JSON data (automatically searches scraping_results/ folder)
python main.py --from-json immoscoop_properties_20250911_200318.json --disable-llm

# Interactive JSON analyzer (easiest to use)
python analyze_json.py --interactive

# Direct JSON analysis
python analyze_json.py my_properties.json

# List available JSON files
python analyze_json.py --list
```

### Command Line Options

**Main Script (main.py):**

*Analysis Mode:*
- `--from-json`: Analyze properties from existing JSON file instead of scraping

*Website Selection:*
- `--website`: Website to scrape - choices: immoweb, immoscoop, zimmo, all (default: immoweb)
- `--websites`: Multiple websites to scrape (alternative to --website)
- `--list-websites`: List available websites and exit
- `--search-url`: Direct search URL to scrape (website auto-detected)

*Filters:*
- `--max-price`: Maximum property price filter
- `--min-surface`: Minimum surface area filter (m²)
- `--epc-scores`: EPC energy scores to include (comma-separated)
- `--postal-codes`: Postal codes to filter by (comma-separated, e.g. "2060,2050" or "BE-2060,BE-2050")
- `--pages`: Number of search result pages to scrape (default: 5)

*Analysis Options:*
- `--disable-llm`: Disable LLM analysis of property descriptions
- `--llm-speed-mode`: Use faster LLM settings (shorter timeouts, less detailed analysis)
- `--enable-geo-analysis`: Enable geolocation analysis (travel times and distances)

*Output:*
- `--output`: Output filename (default: property_analysis.xlsx)

**JSON Analyzer (analyze_json.py):**
- `json_file`: JSON file to analyze (positional argument)
- `--output`: Output Excel filename
- `--list`: List available JSON files in current directory
- `--interactive`: Run in interactive mode with file selection

## Output Structure

The tool automatically organizes all files into separate folders:

### 📁 `scraping_results/`
Contains raw scraping data:
- `immoweb_properties_YYYYMMDD_HHMMSS.json`
- `immoscoop_properties_YYYYMMDD_HHMMSS.json`
- `zimmo_properties_YYYYMMDD_HHMMSS.json`

### 📁 `analysis_results/`
Contains analysis outputs:
- **Excel Report**: Source-specific sheets for each website
- **Analysis JSON**: Detailed analysis data

### Excel Report Structure

For each website source, the Excel file contains:

**For each website (IMMOWEB, IMMOSCOOP, ZIMMO):**
- **`SUM - [WEBSITE]`**: Detailed property summary with all essential columns:
  - LINK, POSTCODE, ADDRESS, PRICE, Surface, bedrooms
  - EPC scores, P-score, G-score
  - Amenities (Garage, Garden, Lift, Balcony, etc.)
  - LLM Analysis (Condition, Summary, Pros/Cons)
- **`TRK - [WEBSITE]`**: Property tracking sheet with essential fields
- **`RAW - [WEBSITE]`**: Complete raw data export

### Travel Time Features (Optional)

When `--enable-geo-analysis` is used:
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
# Analyze existing JSON data from scraping_results/ folder (fastest)
python analyze_json.py --interactive

# Manual data entry tool
python manual_data_input.py

# Load from specific JSON backup (checks both current dir and scraping_results/)
python analyze_json.py properties_backup.json --output custom_analysis.xlsx
```

**Workflow Recommendation:**
1. **First run**: Use `main.py` to scrape and generate organized JSON data
2. **Re-analysis**: Use `analyze_json.py` to analyze existing data with updated features
3. **Manual backup**: Use `manual_data_input.py` if scraping fails completely

**File Organization Benefits:**
- ✅ **Clean workspace**: Separate folders for different file types
- ✅ **Easy navigation**: Find scraping data vs analysis results quickly
- ✅ **Source separation**: Each website gets its own Excel sheets
- ✅ **Backward compatibility**: Still finds files in current directory if needed

## Architecture

Immowbot uses a modular architecture with separate scrapers for each website:

- **Base Scraper** (`src/base_scraper.py`): Abstract interface defining common scraper functionality
- **File Manager** (`src/file_manager.py`): Automatic organization of scraping and analysis files
- **Immoweb Scraper** (`src/scrapers/immoweb_scraper.py`): Specialized for Immoweb.be with JavaScript data extraction
- **Immoscoop Scraper** (`src/scrapers/immoscoop_scraper.py`): Handles React/Next.js content from Immoscoop.be
- **Zimmo Scraper** (`src/scrapers/zimmo_scraper.py`): Pattern-based extraction for Zimmo.be
- **Scraper Manager** (`src/scraper_manager.py`): Coordinates multiple scrapers and combines results
- **Data Exporter** (`src/exporter.py`): Creates source-specific Excel sheets and organized exports
- **LLM Analyzer** (`src/llm_analyzer.py`): Local Ollama integration for property description analysis

## LLM Integration

Immowbot includes local AI analysis capabilities:

- **Local Ollama**: Uses local LLM models (default: phi3:3.8b) for property description analysis
- **Language Support**: Analyzes Dutch property descriptions and outputs insights in English
- **Configurable Speed**: Normal mode for detailed analysis or speed mode for faster processing
- **Property Insights**: Extracts pros and cons from property descriptions automatically

## Legal Notice

This tool is for personal research and educational purposes only. Please respect the terms of service of all scraped websites (Immoweb.be, Immoscoop.be, Zimmo.be) and use reasonable delays between requests. The tool includes built-in delays to be respectful of website resources.

## Requirements

- Python 3.12+
- Chrome browser (for Selenium WebDriver)
- All packages listed in requirements.txt