"""
Base scraper interface for Belgian real estate websites.
"""
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
from .file_manager import FileManager


class BasePropertyScraper(ABC):
    """Abstract base class for property scrapers."""
    
    def __init__(self, website_name: str, base_url: str):
        self.website_name = website_name
        self.base_url = base_url
        self.properties = []
        self.properties_url = []
        self.existing_properties = set()
        self.session = requests.Session()
        self.file_manager = FileManager()
        
        # Common user agent for all scrapers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        })
        
        # Load existing properties to avoid duplicates
        self._load_existing_properties()
    
    def _load_existing_properties(self):
        """Load existing property IDs to avoid duplicates."""
        try:
            latest_file = self.file_manager.get_latest_scraping_file(self.website_name)
            if latest_file:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    for prop in existing_data:
                        if prop.get('id'):
                            self.existing_properties.add(str(prop.get('id')))
                        if prop.get('url'):
                            self.existing_properties.add(prop.get('url'))
                print(f"Loaded {len(self.existing_properties)} existing {self.website_name} properties from {os.path.basename(latest_file)}")
        except Exception as e:
            print(f"Could not load existing {self.website_name} properties: {e}")
    
    # def _setup_chrome_driver(self) -> webdriver.Chrome:
    #     """Set up Chrome driver with anti-detection measures."""
    #     chrome_options = Options()
    #     chrome_options.add_argument("--headless")
    #     chrome_options.add_argument("--no-sandbox")
    #     chrome_options.add_argument("--disable-dev-shm-usage")
    #     chrome_options.add_argument("--disable-gpu")
    #     chrome_options.add_argument("--disable-extensions")
    #     chrome_options.add_argument("--disable-plugins")
    #     chrome_options.add_argument("--disable-images")
    #     # chrome_options.add_argument("--disable-javascript")  # Can be overridden by subclasses
    #     chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    #
    #     # Additional anti-detection options
    #     chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    #     chrome_options.add_experimental_option('useAutomationExtension', False)
    #     chrome_options.add_experimental_option("prefs", {
    #         "profile.default_content_setting_values.notifications": 2,
    #         "profile.default_content_settings.popups": 0,
    #         "profile.managed_default_content_settings.images": 2
    #     })
    #
    #     try:
    #         # Use local chromedriver if available, otherwise use webdriver manager
    #         driver_path = "C:\\Users\\ample\\Documents\\workspace\\projects\\immowbot\\tools\\chromedriver.exe"
    #
    #         if not os.path.exists(driver_path) or os.path.getsize(driver_path) < 1000:
    #             print("Local Chrome driver not found or corrupted, using webdriver manager...")
    #             driver_path = ChromeDriverManager().install()
    #
    #         service = Service(driver_path)
    #         driver = webdriver.Chrome(service=service, options=chrome_options)
    #
    #         # Enhanced anti-detection scripts
    #         driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    #         driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
    #
    #         return driver
    #
    #     except Exception as e:
    #         print(f"Error setting up Chrome driver: {e}")
    #         raise

    def _setup_chrome_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver with enhanced anti-detection options."""
        chrome_options = Options()

        # Enhanced anti-detection options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")

        # Suppress WebGL/GPU warnings
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-webgl")
        chrome_options.add_argument("--disable-webgl2")
        chrome_options.add_argument("--disable-3d-apis")

        # Suppress GCM/push notification errors
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-notifications")

        # Additional suppression
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")  # Only fatal errors
        chrome_options.add_argument("--silent")

        print("🔧 Setting up Chrome driver (headless mode with warnings suppressed)...")

        # More realistic user agent
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Remove automation indicators
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("detach", True)

        # Add prefs to avoid detection
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2
        })

        try:
            driver_path = ChromeDriverManager().install()
            if not driver_path.endswith(".exe"):
                driver_path = os.path.join(os.path.dirname(driver_path), "chromedriver.exe")
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)

            # Enhanced anti-detection scripts
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Override more navigator properties
            driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({state: 'granted'})
                    })
                });
            """)

            # Set more realistic headers
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                "platform": "Win32"
            })

            # Add extra headers to look more like a real browser
            driver.execute_cdp_cmd('Network.enable', {})
            driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                'headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1'
                }
            })

            # Test the driver with a simple page first
            print("🧪 Testing driver with simple page...")
            driver.get("https://httpbin.org/headers")
            time.sleep(2)

            print("✅ Driver setup successful")
            return driver

        except Exception as e:
            print(f"❌ Error setting up Chrome WebDriver: {e}")
            print("Falling back to requests-based scraping...")
            raise e

    def is_property_already_scraped(self, property_identifier: str) -> bool:
        """Check if property was already scraped."""
        return str(property_identifier) in self.existing_properties
    
    def export_to_json(self) -> str:
        """Export properties to JSON file in organized folder."""
        if not self.properties:
            print("No properties to export")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.file_manager.get_scraping_filepath(self.website_name, timestamp)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.properties, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Exported {len(self.properties)} {self.website_name} properties to {filepath}")
        return filepath
    
    def get_all_properties(self) -> List[Dict]:
        """Get all scraped properties."""
        return self.properties
    
    def clear_properties(self):
        """Clear the properties list."""
        self.properties = []
        self.properties_url = []
    
    # Abstract methods that must be implemented by subclasses
    
    @abstractmethod
    def scrape_with_filters(self,  min_price: Optional[int] = None,max_price: Optional[int] = None, min_surface: Optional[int] = None,
                          epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None, 
                          max_pages: int = 5) -> List[Dict]:
        """Scrape properties with filters."""
        pass
    
    @abstractmethod
    def scrape_from_url(self, search_url: str, max_pages: int = 5) -> List[Dict]:
        """Scrape properties from a specific search URL."""
        pass
    
    @abstractmethod
    def _build_search_url(self, min_price: Optional[int] = None, max_price: Optional[int] = None, min_surface: Optional[int] = None,
                         epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None) -> str:
        """Build search URL with filters for the specific website."""
        pass
    
    @abstractmethod
    def _scrape_property_details(self, property_url: str, driver: webdriver.Chrome ) -> Optional[Dict]:
        """Scrape detailed information for a single property."""
        pass
    
    @abstractmethod
    def _extract_property_urls(self, page_source: str, base_url) -> List[str]:
        """Extract property URLs from search results page."""
        pass
    
    # Optional methods that can be overridden by subclasses
    
    def _normalize_property_data(self, raw_data: Dict) -> Dict:
        """Normalize property data to standard format."""
        normalized_data = {
            # Core fields
            'name': raw_data.get('name', ''),
            'url': raw_data.get('url', ''),
            'price': self._normalize_price(raw_data.get('price')),
            'location': raw_data.get('location', ''),
            'postcode': raw_data.get('postcode', ''),
            
            # Property details
            'property_type': self._normalize_property_type(raw_data.get('property_type', raw_data.get('subtype', ''))),
            'surface_area': self._safe_int(raw_data.get('surface_area', raw_data.get('indoor_surface'))),
            'bedrooms': self._safe_int(raw_data.get('bedrooms', raw_data.get('nb_bedrooms'))),
            'rooms': self._safe_int(raw_data.get('rooms', raw_data.get('nb_rooms'))),
            'construction_year': self._safe_int(raw_data.get('construction_year', raw_data.get('year_of_construction'))),
            
            # Energy and condition
            'epc_score': raw_data.get('epc_score', raw_data.get('energy_certificate', '')),
            'building_state': raw_data.get('building_state', ''),
            
            # Features
            'kitchen_type': raw_data.get('kitchen_type', ''),
            'outdoor_surface': self._safe_float(raw_data.get('outdoor_surface', raw_data.get('terrace_surface'))),
            'outdoor_terrace': raw_data.get('outdoor_terrace', raw_data.get('outdoor_terrace_exists', False)),
            'parking': raw_data.get('parking', ''),
            
            # Location data
            'latitude': self._safe_float(raw_data.get('latitude')),
            'longitude': self._safe_float(raw_data.get('longitude')),
            
            # Additional Immoscoop-specific fields
            'bathrooms': self._safe_int(raw_data.get('bathrooms')),
            'renovation_year': self._safe_int(raw_data.get('renovation_year')),
            'terrain_area': self._safe_int(raw_data.get('terrain_area')),
            'agent_name': raw_data.get('agent_name', ''),
            'agent_phone': raw_data.get('agent_phone', ''),
            'agent_email': raw_data.get('agent_email', ''),
            'image_count': self._safe_int(raw_data.get('image_count', 0)),
            
            # Address components
            'address': raw_data.get('address', ''),
            'street': raw_data.get('street', ''),
            'house_number': raw_data.get('house_number', ''),
            'city': raw_data.get('city', ''),
            'municipality': raw_data.get('municipality', ''),
            
            # Description
            'description': raw_data.get('description', ''),
            
            # Metadata
            'source_website': self.website_name,
            'scraped_at': datetime.now().isoformat(),
            'data_source': raw_data.get('data_source', 'html_parsing'),
        }
        
        # Preserve comprehensive property details if available (Immoscoop enriched data)
        if 'property_details' in raw_data:
            normalized_data['property_details'] = raw_data['property_details']
        
        # Preserve individual category details if available
        for detail_type in ['financial_details', 'building_details', 'terrain_details', 
                           'location_details', 'layout_details', 'comfort_details', 
                           'energy_details', 'urban_planning_details', 'all_property_details']:
            if detail_type in raw_data:
                normalized_data[detail_type] = raw_data[detail_type]
        
        # Preserve any additional fields that might be website-specific
        for key in ['id', 'title', 'meta_title']:
            if key in raw_data:
                normalized_data[key] = raw_data[key]
        
        return normalized_data
    
    def _normalize_price(self, price) -> float:
        """Normalize price to float."""
        if isinstance(price, (int, float)):
            return float(price)
        
        if isinstance(price, str):
            # Remove currency symbols and spaces
            price_str = price.replace('€', '').replace(',', '').replace(' ', '').strip()
            try:
                return float(price_str)
            except ValueError:
                pass
        
        return 0.0
    
    def _normalize_property_type(self, prop_type: str) -> str:
        """Normalize property type to standard values."""
        if not prop_type:
            return ''
        
        prop_type = prop_type.lower()
        
        if 'apartment' in prop_type or 'flat' in prop_type:
            return 'apartment'
        elif 'house' in prop_type or 'villa' in prop_type or 'bungalow' in prop_type:
            return 'house'
        elif 'studio' in prop_type:
            return 'studio'
        else:
            return prop_type
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int."""
        if isinstance(value, int):
            return value
        
        if isinstance(value, str) and value.strip():
            try:
                return int(float(value.strip()))
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float."""
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str) and value.strip():
            try:
                return float(value.strip())
            except (ValueError, TypeError):
                pass

        return None

    def _normalize_epc_label(self, value):
        if not value:
            return ""
        text = str(value).strip().upper()
        for label in ("A++", "A+", "A", "B", "C", "D", "E", "F", "G"):
            if text.startswith(label):
                return label
        return ""