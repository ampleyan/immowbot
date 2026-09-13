"""
Configuration settings for Immowbot.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Scraping settings
DEFAULT_MAX_PAGES = 5
REQUEST_DELAY = 2  # seconds between requests
PAGE_LOAD_TIMEOUT = 10  # seconds to wait for page load

# Chrome driver options
CHROME_OPTIONS = [
    "--headless",
    "--no-sandbox", 
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1920,1080"
]

# Data export settings
EXPORT_FORMATS = ['xlsx', 'csv', 'notion']
DEFAULT_OUTPUT_FILE = 'property_analysis.xlsx'

# Notion integration settings
NOTION_API_KEY = os.getenv('NOTION_API_KEY', '')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID', '')

# Analysis settings
PRICE_RANGES = {
    'budget': (0, 150000),
    'mid_range': (150000, 250000),
    'premium': (250000, 350000),
    'luxury': (350000, float('inf'))
}

# EPC score hierarchy (best to worst)
EPC_HIERARCHY = ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']

# Common postcodes in Belgium for validation
BELGIAN_POSTCODE_PATTERN = r'\b[1-9]\d{3}\b'