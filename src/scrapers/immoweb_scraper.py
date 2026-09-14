"""
Immoweb.be scraper - refactored to use base scraper architecture.
"""
from typing import List, Dict, Optional
from urllib.parse import urlencode
import time
import json
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from ..base_scraper import BasePropertyScraper
from ..translator import PropertyTranslator
import requests

try:
    import undetected_chromedriver as uc
    _UC_AVAILABLE = True
except ImportError:
    _UC_AVAILABLE = False


class ImmowebScraper(BasePropertyScraper):
    """Scraper for Immoweb.be - Belgium's largest real estate platform."""
    
    def __init__(self):
        super().__init__("Immoweb", "https://www.immoweb.be")
        # Initialize session for fallback requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        # Initialize translator
        self.translator = PropertyTranslator()

    def _setup_chrome_driver(self):
        if _UC_AVAILABLE:
            chrome_version = self._detect_chrome_version()
            try:
                print("🔧 Setting up undetected Chrome driver (headless mode)...")
                options = uc.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--headless=new")
                options.add_argument("--disable-background-networking")
                options.add_argument("--disable-notifications")
                kwargs = {"options": options}
                if chrome_version:
                    kwargs["version_main"] = chrome_version
                driver = uc.Chrome(**kwargs)
                print("✅ Undetected Chrome driver ready")
                return driver
            except Exception as exc:
                print(f"⚠ undetected-chromedriver failed ({exc}), falling back to standard driver")
        return super()._setup_chrome_driver()

    def _detect_chrome_version(self):
        import subprocess, os
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run(
                        ["powershell", "-Command",
                         f"(Get-Item '{path}').VersionInfo.ProductVersion"],
                        capture_output=True, text=True, timeout=5
                    )
                    major = int(result.stdout.strip().split(".")[0])
                    return major
                except Exception:
                    pass
        return None

    def _build_search_url(self, max_price: Optional[int] = None, min_surface: Optional[int] = None,
                         epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None) -> str:
        """Build Immoweb search URL with filters."""
        base_search_url = "https://www.immoweb.be/en/search"
        
        # Build filter parameters
        params = {
            'countries': 'BE',
            'page': '1',
            'orderBy': 'relevance'
        }
        
        if max_price:
            params['maxPrice'] = str(max_price)
        
        if min_surface:
            params['minSurface'] = str(min_surface)
        
        if epc_scores:
            # Clean and format EPC scores for Immoweb
            clean_scores = []
            for score in epc_scores:
                score = score.replace('BE-', '').strip()
                if score in ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']:
                    clean_scores.append(score)
            if clean_scores:
                params['energyClasses'] = ','.join(clean_scores)
        
        if postal_codes:
            # Clean postal codes
            clean_codes = []
            for code in postal_codes:
                code = code.replace('BE-', '').strip()
                if code.isdigit() and len(code) == 4:
                    clean_codes.append(code)
            if clean_codes:
                params['postalCodes'] = 'BE-' + ',BE-'.join(clean_codes)
        
        # Build URL with parameters
        if params:
            return f"{base_search_url}?{urlencode(params)}"
        else:
            return f"{base_search_url}/apartment/for-sale"
    
    def scrape_with_filters(self, max_price: Optional[int] = None, min_surface: Optional[int] = None, 
                          epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None, 
                          max_pages: int = 5, on_listing=None, on_checked=None,
                          should_cancel=None) -> List[Dict]:
        """Scrape Immoweb with filters."""
        search_url = self._build_search_url(max_price, min_surface, epc_scores, postal_codes)
        print(f"🌐 Scraping Immoweb with URL: {search_url}")
        
        return self.scrape_from_url(search_url, max_pages, on_listing, on_checked, should_cancel)
    
    def scrape_from_url(self, search_url: str, max_pages: int = 5, on_listing=None,
                        on_checked=None, should_cancel=None) -> List[Dict]:
        """Scrape Immoweb from a specific search URL."""
        # Load existing properties using base class method
        if hasattr(self, 'load_existing_properties'):
            self.load_existing_properties()
        else:
            # Fallback - load from base class properties tracking
            print("🔍 Loading existing properties from previous sessions...")
            # Base class handles existing properties automatically
        
        properties = []
        driver = None
        
        try:
            # Set up Chrome driver with enhanced anti-detection
            driver = self._setup_chrome_driver()
            
            # Skip stealth mode for UC driver (it handles this internally)
            self._apply_advanced_stealth_mode(driver)

            using_uc = _UC_AVAILABLE and isinstance(driver, uc.Chrome)
            cloudflare_wait = 20 if using_uc else 3

            print("   Visiting homepage to establish session...")
            driver.get("https://www.immoweb.be")
            time.sleep(cloudflare_wait)

            if self._check_for_captcha(driver):
                print("   CAPTCHA detected on homepage - scraping may be limited")
                # Continue anyway — search pages sometimes work regardless
            
            print(f"🚀 Starting Immoweb scraping for {max_pages} pages...")
            
            for page in range(1, max_pages + 1):
                # Update page number in URL
                url = self._update_page_number(search_url, page)
                print(f"\n📄 Scraping Immoweb page {page}/{max_pages}...")
                print(f"   URL: {url}")
                
                driver.get(url)
                time.sleep(5)  # Longer wait for page to load
                
                # Check for CAPTCHA on search pages
                if self._check_for_captcha(driver):
                    print(f"   ⚠ CAPTCHA detected on page {page} - implementing delays...")
                    time.sleep(15)  # Longer wait when CAPTCHA detected
                    
                    # Try refreshing once
                    driver.refresh()
                    time.sleep(8)
                    
                    if self._check_for_captcha(driver):
                        print(f"   ❌ CAPTCHA persists on page {page} - skipping...")
                        continue
                
                # Wait for property listings to load
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "card__title-link"))
                    )
                except:
                    print(f"No property listings found on page {page}")
                    break
                
                # Extract property links using the correct selectors
                property_cards = driver.find_elements(By.CLASS_NAME, "card__title-link")
                if not property_cards:
                    print(f"No more properties found on page {page}")
                    break
                
                page_urls = []
                for card in property_cards:
                    try:
                        # Get property URL using the correct selector for the title link
                        href = card.get_attribute("href")
                        if href and "/classified/" in href:
                            page_urls.append(href)
                    except Exception as e:
                        print(f"Error extracting property card: {e}")
                        continue

                time.sleep(5)  # Be respectful with requests
                
                print(f"   Found {len(page_urls)} property URLs on page {page}")

                for i, property_url in enumerate(page_urls, 1):
                    if should_cancel and should_cancel():
                        break
                    if not self._postcode_allowed(property_url):
                        print(f"   ⏭️  [{i}/{len(page_urls)}] Skipping postcode mismatch: {property_url}")
                        if on_checked:
                            on_checked()
                        continue
                    # Check if property was already scraped
                    if self.is_property_already_scraped(property_url):
                        print(f"   ⏭️  [{i}/{len(page_urls)}] Skipping already scraped property")
                        continue
                    
                    # URL is already full, no need for urljoin
                    print(f"   [{i}/{len(page_urls)}] Scraping: {property_url}")
                    property_data = self._scrape_property_details(property_url, driver)
                    if property_data:
                        # The property_data is already in the expected format from original scraper
                        # But we need to ensure it's compatible with the base class structure
                        normalized_data = self._normalize_property_data(property_data)
                        
                        self.properties.append(normalized_data)
                        properties.append(normalized_data)  # Keep for return value
                        if on_listing:
                            on_listing(normalized_data)
                        print(f"   ✅ Scraped: {normalized_data.get('name', 'N/A')} - €{normalized_data.get('price', 'N/A'):,.0f}")
                        
                        # Add to existing properties to avoid re-scraping in same session
                        if normalized_data.get('id'):
                            self.existing_properties.add(str(normalized_data.get('id')))
                        self.existing_properties.add(property_url)
                    else:
                        print(f"   ❌ Failed to scrape property")
                    if on_checked:
                        on_checked()
                    if should_cancel and should_cancel():
                        break
                    time.sleep(8)  # Longer delays to avoid CAPTCHA

                if should_cancel and should_cancel():
                    break

        finally:
            if driver:
                driver.quit()
        
        # Auto-export to JSON if properties were found (using base class method)
        if properties:
            self.export_to_json()
        
        # Print final summary
        successfully_scraped = len(properties)
        print(f"\n🎉 Immoweb Scraping Summary:")
        print(f"   ✅ Successfully scraped: {successfully_scraped}")
        if successfully_scraped > 0:
            print(f"   🏠 Average price: €{sum(p.get('price', 0) for p in properties) / len(properties):,.0f}")
        
        return properties
    
    def _scrape_property_details(self, property_url: str, driver=None) -> Optional[Dict]:
        """Scrape detailed information for a single Immoweb property."""
        if not driver:
            # This shouldn't happen in the refactored version, but handle it gracefully
            print("Warning: No driver provided to _scrape_property_details")
            return None
        
        try:
            print(f"   Accessing property: {property_url}")
            driver.get(property_url)
            
            # Wait for main content to load
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "main"))
                )
            except TimeoutException:
                print("⚠ Timeout waiting for main content")
            
            # Human-like behavior
            time.sleep(2)
            
            try:
                # Try to get av_items from JavaScript
                av_items = None
                try:
                    av_items = driver.execute_script("return av_items;")
                except:
                    pass
                
                classified_data = {}
                
                if av_items and isinstance(av_items, list) and len(av_items) > 0:
                    print("   ✓ Using JavaScript av_items data")

                    # Try to get comprehensive window.classified data
                    try:
                        classified_data = driver.execute_script("return window.classified || {};")
                        if classified_data and 'property' in classified_data:
                            # Use comprehensive extraction
                            property_data = self._extract_comprehensive_data_from_classified(classified_data)
                            print("   ✓ Enhanced with window.classified comprehensive data")
                        else:
                            # Fall back to av_items only
                            property_data = av_items[0]
                            property_data['street'] = self._extract_location(driver)
                            property_data['all_property_details'] = {}
                    except Exception as e:
                        # Fall back to av_items only
                        property_data = av_items[0]
                        property_data['street'] = self._extract_location(driver)
                        property_data['all_property_details'] = {}
                else:
                    # Fallback: Parse from classified data in HTML
                    print("   ⚠ JavaScript data not available, using HTML parsing fallback")

                    try:
                        response = self.session.get(property_url, timeout=10)

                        if response.status_code != 200:
                            print(f"   ❌ HTTP error {response.status_code}")
                            return None

                        match = re.search(r'window\.classified\s*=\s*({.*?});', response.text, re.DOTALL)
                        if match:
                            try:
                                json_str = match.group(1)
                                classified_data = json.loads(json_str)

                                # Use comprehensive extraction method
                                property_data = self._extract_comprehensive_data_from_classified(classified_data)

                                print("   ✓ Successfully extracted comprehensive classified data from HTML")

                            except (json.JSONDecodeError, KeyError) as e:
                                print(f"   ⚠ Failed to parse classified data: {e}")
                                print("   ⚠ Attempting full HTML fallback parsing...")
                                property_data = self._fallback_html_parsing(property_url, response)
                                if not property_data or not property_data.get('price'):
                                    return None
                        else:
                            print("   ⚠ No window.classified found, attempting full HTML fallback...")
                            property_data = self._fallback_html_parsing(property_url, response)
                            if not property_data or not property_data.get('price'):
                                print("   ❌ Fallback parsing failed - no valid data")
                                return None

                    except requests.exceptions.RequestException as e:
                        print(f"   ❌ Request failed: {e}")
                        return None
                    except Exception as e:
                        print(f"   ❌ Unexpected error in fallback: {e}")
                        return None
                
                # Normalize price
                price = self._normalize_price(property_data.get('price', 0))
                
                # Build standardized property details
                details = {
                    'id': property_data.get('id'),
                    'url': property_url,
                    'name': property_data.get('street', property_data.get('location', '')),
                    'price': price,
                    'location': f"{property_data.get('city', '')}, {property_data.get('zip_code', '')}, {property_data.get('street', '')}".strip(),
                    'postcode': property_data.get('zip_code'),
                    'property_type': property_data.get('subtype', ''),
                    'surface_area': self._safe_int(property_data.get('indoor_surface')),
                    'bedrooms': self._safe_int(property_data.get('nb_bedrooms')),
                    'construction_year': self._safe_int(property_data.get('year_of_construction')),
                    'epc_score': self._normalize_epc_label(property_data.get('energy_certificate', '')),
                    'latitude': self._safe_float(property_data.get('latitude')),
                    'longitude': self._safe_float(property_data.get('longitude')),
                    'description': property_data.get('description', ''),
                    'source': 'immoweb',  # Source website identifier
                    'all_property_details': property_data.get('all_property_details', {})  # Comprehensive property details
                }

                return details
                
            except Exception as e:
                print(f"   Error parsing property data: {e}")
                return None
            
        except Exception as e:
            print(f"   Error scraping property: {e}")
            return None
    
    def _extract_property_urls(self, page_source: str, base_url: str = None) -> List[str]:
        """Extract property URLs from Immoweb search results page."""
        # This method is used by the base class but in our case we extract URLs directly with Selenium
        return []
    
    def _extract_location(self, driver) -> str:
        """Extract location from Immoweb property page."""
        try:
            # Try different selectors for location
            location_element = driver.find_element(By.CSS_SELECTOR, '.classified__information--address-row')
            location_text = location_element.text.strip()
            return location_text
        except:
            return ""
    
    def _update_page_number(self, url: str, page: int) -> str:
        """Update the page number in a search URL."""
        if "page=" in url:
            return re.sub(r'page=\d+', f'page={page}', url)
        else:
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}page={page}"
    
    def _simulate_human_behavior(self, driver):
        """Add human-like behavior to avoid bot detection."""
        import random
        
        # Random scroll
        scroll_amount = random.randint(100, 500)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.5, 1.5))
        
        # Scroll back up a bit
        driver.execute_script(f"window.scrollBy(0, -{scroll_amount // 2});")
        time.sleep(random.uniform(0.2, 0.8))
    
    def _parse_coordinates(self, geolocation_str):
        """Parse 'lng,lat' string into tuple (lat, lng)"""
        if geolocation_str and ',' in geolocation_str:
            try:
                lng, lat = geolocation_str.split(',')
                return (float(lat.strip()), float(lng.strip()))
            except (ValueError, IndexError):
                pass
        return None

    def _safe_int(self, value):
        """Safely convert value to int."""
        if value is None or value == '':
            return None
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None

    def _safe_float(self, value):
        """Safely convert value to float."""
        if value is None or value == '':
            return None
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return None

    def _safe_bool(self, value):
        """Safely convert value to bool."""
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value) if value is not None else None

    def _check_tenant_situation(self, description: str, transaction: Dict) -> bool:
        """Check if property has current tenants."""
        tenant_keywords = [
            'tenant', 'rented', 'occupied', 'huurder', 'verhuurd', 'bezet',
            'rental income', 'current rent', 'lease', 'huurcontract',
            'locataire', 'loué', 'actuellement loué', 'currently rented'
        ]

        # Check description
        if description:
            desc_lower = description.lower()
            for keyword in tenant_keywords:
                if keyword in desc_lower:
                    return True

        # Check transaction data for rental info
        rental = transaction.get('rental', {})
        if rental and rental.get('monthlyRentalPrice'):
            return True

        return False

    def _extract_comprehensive_data_from_classified(self, classified_data: Dict) -> Dict:
        """Extract comprehensive property data from window.classified JSON with multi-source fallback."""
        prop = classified_data.get('property', {})
        location = prop.get('location', {})
        price_info = classified_data.get('price', {})
        transaction = classified_data.get('transaction', {})
        certificates = transaction.get('certificates', {})
        sale = transaction.get('sale', {})
        building = prop.get('building', {})
        energy = prop.get('energy', {})
        kitchen = prop.get('kitchen', {})
        land = prop.get('land', {})
        flags = classified_data.get('flags', {})

        # Extract all property details into a comprehensive dictionary
        all_details = {}

        # Building details
        all_details['Facade count'] = building.get('facadeCount')
        all_details['Floor count'] = building.get('floorCount')
        all_details['Street facade width'] = building.get('streetFacadeWidth')
        all_details['Construction year'] = building.get('constructionYear')
        all_details['State building'] = building.get('condition')
        all_details['Annex count'] = building.get('annexCount')

        # Location details
        all_details['Floor'] = location.get('floor')
        all_details['Box'] = location.get('box')
        all_details['Property name'] = location.get('propertyName')
        all_details['Region'] = location.get('region')
        all_details['Province'] = location.get('province')
        all_details['District'] = location.get('district')

        # Room counts
        all_details['Bedrooms'] = prop.get('bedroomCount')
        all_details['Bathrooms'] = prop.get('bathroomCount')
        all_details['Shower rooms'] = prop.get('showerRoomCount')
        all_details['Toilets'] = prop.get('toiletCount')
        all_details['Rooms'] = prop.get('roomCount')

        # Surface areas
        all_details['Surface'] = prop.get('netHabitableSurface')
        all_details['Bedroom surface'] = prop.get('bedroomSurface')
        all_details['Living room surface'] = prop.get('livingRoom', {}).get('surface') if isinstance(prop.get('livingRoom'), dict) else None
        all_details['Dining room surface'] = prop.get('diningRoom', {}).get('surface') if isinstance(prop.get('diningRoom'), dict) else None
        all_details['Kitchen surface'] = kitchen.get('surface')
        all_details['Garden surface'] = prop.get('gardenSurface')
        all_details['Terrace surface'] = prop.get('terraceSurface')
        all_details['Land surface'] = land.get('surface') if land else None

        # Kitchen details
        all_details['Type of kitchen'] = kitchen.get('type')
        all_details['Kitchen has oven'] = kitchen.get('hasOven')
        all_details['Kitchen has microwave'] = kitchen.get('hasMicroWaveOven')
        all_details['Kitchen has dishwasher'] = kitchen.get('hasDishwasher')
        all_details['Kitchen has washing machine'] = kitchen.get('hasWashingMachine')
        all_details['Kitchen has fridge'] = kitchen.get('hasFridge')

        # Energy & utilities
        all_details['EPC score'] = certificates.get('epcScore')
        all_details['EPC label'] = certificates.get('epcScore')
        all_details['EPC score (kWh/(m² years))'] = certificates.get('primaryEnergyConsumptionPerSqm')
        all_details['EPC reference'] = certificates.get('epcReference')
        all_details['Carbon emission'] = certificates.get('carbonEmission')
        all_details['Renovation obligation'] = certificates.get('renovationObligation')
        all_details['Heating type'] = energy.get('heatingType')
        all_details['Type of glazing'] = 'Double glazing' if energy.get('hasDoubleGlazing') else 'Single glazing' if energy.get('hasDoubleGlazing') == False else None
        all_details['Double glazing'] = 'Yes' if energy.get('hasDoubleGlazing') else 'No' if energy.get('hasDoubleGlazing') == False else None
        all_details['Photovoltaic panels'] = 'Yes' if energy.get('hasPhotovoltaicPanels') else 'No' if energy.get('hasPhotovoltaicPanels') == False else None
        all_details['Thermic panels'] = 'Yes' if energy.get('hasThermicPanels') else 'No' if energy.get('hasThermicPanels') == False else None
        all_details['Heat pump'] = 'Yes' if energy.get('hasHeatPump') else 'No' if energy.get('hasHeatPump') == False else None

        # Property features (amenities)
        all_details['Garden'] = 'Yes' if prop.get('hasGarden') else 'No' if prop.get('hasGarden') == False else None
        all_details['Garden orientation'] = prop.get('gardenOrientation')
        all_details['Terrace'] = 'Yes' if prop.get('hasTerrace') else 'No' if prop.get('hasTerrace') == False else None
        all_details['Terrace orientation'] = prop.get('terraceOrientation')
        all_details['Balcony'] = 'Yes' if prop.get('hasBalcony') else 'No' if prop.get('hasBalcony') == False else None
        all_details['Lift'] = 'Yes' if prop.get('hasLift') else 'No' if prop.get('hasLift') == False else None
        all_details['Garage'] = 'Yes' if (prop.get('parkingCountClosedBox') or 0) > 0 else None
        all_details['Parking indoor'] = prop.get('parkingCountIndoor')
        all_details['Parking outdoor'] = prop.get('parkingCountOutdoor')
        all_details['Parking closed box'] = prop.get('parkingCountClosedBox')
        all_details['Swimming pool'] = 'Yes' if prop.get('hasSwimmingPool') else 'No' if prop.get('hasSwimmingPool') == False else None
        all_details['Sauna'] = 'Yes' if prop.get('hasSauna') else 'No' if prop.get('hasSauna') == False else None
        all_details['Jacuzzi'] = 'Yes' if prop.get('hasJacuzzi') else 'No' if prop.get('hasJacuzzi') == False else None
        all_details['Basement'] = 'Yes' if prop.get('hasBasement') else 'No' if prop.get('hasBasement') == False else None
        all_details['Attic'] = 'Yes' if prop.get('hasAttic') else 'No' if prop.get('hasAttic') == False else None
        all_details['Dressing room'] = 'Yes' if prop.get('hasDressingRoom') else 'No' if prop.get('hasDressingRoom') == False else None
        all_details['Laundry room'] = 'Yes' if prop.get('hasLaundryRoom') else 'No' if prop.get('hasLaundryRoom') == False else None

        # Security & accessibility
        all_details['Secure access alarm'] = 'Yes' if prop.get('hasSecureAccessAlarm') else 'No' if prop.get('hasSecureAccessAlarm') == False else None
        all_details['Armored door'] = 'Yes' if prop.get('hasArmoredDoor') else 'No' if prop.get('hasArmoredDoor') == False else None
        all_details['Disabled access'] = 'Yes' if prop.get('hasDisabledAccess') else 'No' if prop.get('hasDisabledAccess') == False else None
        all_details['Door phone'] = 'Yes' if prop.get('hasDoorPhone') else 'No' if prop.get('hasDoorPhone') == False else None
        all_details['Visiophone'] = 'Yes' if prop.get('hasVisiophone') else 'No' if prop.get('hasVisiophone') == False else None
        all_details['Caretaker or concierge'] = 'Yes' if prop.get('hasCaretakerOrConcierge') else 'No' if prop.get('hasCaretakerOrConcierge') == False else None

        # Other amenities
        all_details['Air conditioning'] = 'Yes' if prop.get('hasAirConditioning') else 'No' if prop.get('hasAirConditioning') == False else None
        all_details['Fireplace'] = 'Yes' if prop.get('fireplaceExists') else 'No' if prop.get('fireplaceExists') == False else None
        all_details['Fireplace count'] = prop.get('fireplaceCount')
        all_details['Tennis court'] = 'Yes' if prop.get('hasTennisCourt') else 'No' if prop.get('hasTennisCourt') == False else None
        all_details['Barbecue'] = 'Yes' if prop.get('hasBarbecue') else 'No' if prop.get('hasBarbecue') == False else None
        all_details['Hammam'] = 'Yes' if prop.get('hasHammam') else 'No' if prop.get('hasHammam') == False else None
        all_details['Fitness room'] = 'Yes' if prop.get('hasFitnessRoom') else 'No' if prop.get('hasFitnessRoom') == False else None

        # Financial & legal
        all_details['Cadastral income'] = sale.get('cadastralIncome')
        all_details['Monthly costs'] = prop.get('monthlyCosts')
        all_details['Subject to VAT'] = 'Yes' if sale.get('isSubjectToVat') else 'No' if sale.get('isSubjectToVat') == False else None
        all_details['Furnished'] = 'Yes' if sale.get('isFurnished') else 'No' if sale.get('isFurnished') == False else None
        all_details['Price per sqm'] = sale.get('pricePerSqm')
        all_details['Old price'] = sale.get('oldPrice')

        # Property status flags
        all_details['First occupation'] = 'Yes' if prop.get('isFirstOccupation') else 'No' if prop.get('isFirstOccupation') == False else None
        all_details['Holiday property'] = 'Yes' if prop.get('isHolidayProperty') else 'No' if prop.get('isHolidayProperty') == False else None
        all_details['Under option'] = 'Yes' if flags.get('isUnderOption') else 'No' if flags.get('isUnderOption') == False else None
        all_details['Newly built'] = 'Yes' if flags.get('isNewlyBuilt') else 'No' if flags.get('isNewlyBuilt') == False else None
        all_details['Life annuity sale'] = 'Yes' if flags.get('isLifeAnnuitySale') else 'No' if flags.get('isLifeAnnuitySale') == False else None
        all_details['Public sale'] = 'Yes' if flags.get('isPublicSale') else 'No' if flags.get('isPublicSale') == False else None

        # Extract all property images
        media = classified_data.get('media', {})
        pictures = media.get('pictures', [])
        images = [picture.get('largeUrl') or picture.get('mediumUrl') or picture.get('url') for picture in pictures if isinstance(picture, dict)]
        images = [image for image in images if image]
        all_details['Image 1 URL'] = pictures[0].get('largeUrl') if len(pictures) > 0 else None
        all_details['Image 2 URL'] = pictures[1].get('largeUrl') if len(pictures) > 1 else None

        # Check for tenant situation from description
        description = (
            prop.get('alternativeDescriptions', {}).get('nl', '') or
            prop.get('alternativeDescriptions', {}).get('fr', '') or
            prop.get('description', '')
        )
        has_tenant = self._check_tenant_situation(description, transaction)

        # Add critical flags to all_details for visibility
        all_details['HAS_TENANT'] = '⚠️ YES' if has_tenant else 'No'
        all_details['UNDER_OPTION'] = '🔒 YES' if flags.get('isUnderOption') else 'No'

        # Translate description to English
        translation_result = self.translator.translate_property_description(description)
        description_english = translation_result['translated']
        detected_lang = translation_result['detected_language']

        all_details['Description Language'] = detected_lang.upper()
        all_details['Description (Original)'] = translation_result['original']
        all_details['Description (English)'] = description_english

        # Build basic property_data structure with backward compatibility
        property_data = {
            'id': classified_data.get('id'),
            'price': price_info.get('mainValue', 0),
            'street': f"{location.get('street', '')} {location.get('number', '')}".strip(),
            'city': location.get('locality', ''),
            'zip_code': location.get('postalCode', ''),
            'subtype': prop.get('subtype', '').lower(),
            'indoor_surface': prop.get('netHabitableSurface'),
            'nb_bedrooms': prop.get('bedroomCount'),
            'year_of_construction': building.get('constructionYear'),
            'energy_certificate': certificates.get('epcScore'),
            'latitude': location.get('latitude'),
            'longitude': location.get('longitude'),
            'description': description,
            'description_english': description_english,  # Translated description
            'description_language': detected_lang,
            'all_property_details': all_details,
            'has_tenant': has_tenant,  # Flag for easy filtering
            'under_option': flags.get('isUnderOption', False),  # Flag for easy filtering
            'image_url_1': all_details.get('Image 1 URL'),
            'image_url_2': all_details.get('Image 2 URL'),
            'images': images,
        }

        return property_data
    
    def _fallback_html_parsing(self, property_url: str, response) -> Dict:
        """Fallback method to parse property data from HTML when JavaScript data unavailable."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.content, 'html.parser')

            property_data = {
                'price': self._extract_price_requests(soup),
                'location': self._extract_location_requests(soup),
                'postcode': None,
                'surface_area': self._extract_surface_area_requests(soup),
                'epc_score': self._extract_epc_score_requests(soup),
                'property_type': self._extract_property_type_requests(soup),
                'bedrooms': self._extract_bedrooms_requests(soup),
                'construction_year': self._extract_construction_year_requests(soup),
                'id': self._extract_id_from_url(property_url),
                'currency': 'eur',
                'street': self._extract_location_requests(soup) or '',
                'city': '',
                'province': '',
                'latitude': None,
                'longitude': None,
                'description': '',
                'indoor_surface': None,
                'nb_bedrooms': None,
                'year_of_construction': None,
                'energy_certificate': None,
                'zip_code': None,
                'subtype': None
            }

            # Extract postcode from location
            if property_data.get('location'):
                postcode_match = re.search(r'\b(\d{4})\b', property_data['location'])
                if postcode_match:
                    property_data['postcode'] = postcode_match.group(1)
                    property_data['zip_code'] = postcode_match.group(1)

            # Try to find description in HTML - multiple approaches
            desc_text = None

            # Try meta tag first (most reliable)
            meta_desc = soup.find('meta', {'itemprop': 'description'})
            if meta_desc and meta_desc.get('content'):
                desc_text = meta_desc.get('content').strip()

            # Try description div with ID
            if not desc_text:
                desc_element = soup.find('div', {'id': 'classified-description-content-text'})
                if desc_element:
                    desc_text = desc_element.get_text(strip=True)

            # Try section description class
            if not desc_text:
                desc_section = soup.find('div', class_='text-block classified__section--description')
                if desc_section:
                    desc_text = desc_section.get_text(strip=True)

            # Fallback to original selectors
            if not desc_text:
                desc_element = soup.find('div', {'data-testid': 'description'}) or soup.find('div', class_='classified__description')
                if desc_element:
                    desc_text = desc_element.get_text(strip=True)

            if desc_text:
                property_data['description'] = desc_text

            # Try to extract additional details from HTML tables or structured data
            all_property_details = {}

            # Look for property details tables (common pattern on Immoweb)
            tables = soup.find_all('table', class_=lambda x: x and 'classified' in x.lower() if x else False)
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            all_property_details[key] = value

            # Look for definition lists (dl/dt/dd pattern)
            dl_elements = soup.find_all('dl')
            for dl in dl_elements:
                dts = dl.find_all('dt')
                dds = dl.find_all('dd')
                for dt, dd in zip(dts, dds):
                    key = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    if key and value:
                        all_property_details[key] = value

            # Extract from meta tags
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                if meta.get('property') and meta.get('content'):
                    prop_name = meta.get('property').replace('og:', '').replace('property:', '').title()
                    all_property_details[prop_name] = meta.get('content')

            # Try to extract structured data (JSON-LD)
            try:
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    if script.string:
                        structured_data = json.loads(script.string)
                        if isinstance(structured_data, dict):
                            # Extract relevant fields
                            if 'address' in structured_data:
                                addr = structured_data['address']
                                if isinstance(addr, dict):
                                    all_property_details['Structured Address'] = addr.get('streetAddress')
                                    if not property_data.get('zip_code'):
                                        property_data['zip_code'] = addr.get('postalCode')
                                    if not property_data.get('city'):
                                        property_data['city'] = addr.get('addressLocality')
            except (json.JSONDecodeError, AttributeError):
                pass

            property_data['all_property_details'] = all_property_details
            print(f"   ✓ HTML parsing completed ({len(all_property_details)} additional fields extracted)")
            return property_data

        except Exception as e:
            print(f"   ❌ Fallback HTML parsing error: {e}")
            return None
    
    def _extract_price_requests(self, soup) -> Optional[str]:
        """Extract price using BeautifulSoup."""
        try:
            # Look for price in various possible selectors
            price_selectors = [
                '[data-testid="price"]',
                '.classified__price',
                '.price',
                'span[class*="price"]'
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    price_match = re.search(r'€\s*([\d,]+)', price_text)
                    if price_match:
                        return price_match.group(1).replace(',', '')
            
            # Fallback: look for any element containing price
            price_pattern = re.compile(r'€\s*([\d,]+)')
            all_text = soup.get_text()
            price_matches = price_pattern.findall(all_text)
            if price_matches:
                return price_matches[0].replace(',', '')
                
        except Exception:
            pass
        return None
    
    def _extract_location_requests(self, soup) -> Optional[str]:
        """Extract location using BeautifulSoup."""
        try:
            # Look for location in breadcrumb or title
            location_selectors = [
                '[data-testid="breadcrumb"] span:last-child',
                'h1',
                'h2',
                '.classified__title',
                '.classified__information--address-row'
            ]
            
            for selector in location_selectors:
                location_element = soup.select_one(selector)
                if location_element:
                    return location_element.get_text(strip=True)
        except Exception:
            pass
        return None
    
    def _extract_surface_area_requests(self, soup) -> Optional[str]:
        """Extract surface area using BeautifulSoup."""
        try:
            # Look for surface area in text
            text = soup.get_text()
            surface_matches = re.findall(r'(\d+)\s*m²', text)
            if surface_matches:
                # Return the largest surface area found (likely living area)
                return max(surface_matches, key=int)
        except Exception:
            pass
        return None
    
    def _extract_epc_score_requests(self, soup) -> Optional[str]:
        """Extract EPC score using BeautifulSoup."""
        try:
            # Look for EPC image with class "classified-table__picture"
            epc_imgs = soup.find_all('img', class_='classified-table__picture')
            
            for img in epc_imgs:
                src = img.get('src', '')
                if 'epc/pics/peb' in src:
                    # Extract energy class from filename (letter before .png)
                    match = re.search(r'/([a-g](?:plus)*|[a-g][+]*|[a-g]__)\.png$', src, re.IGNORECASE)
                    if match:
                        energy_class = match.group(1).upper()
                        # Handle A+ and A++ variants
                        if energy_class == "APLUS":
                            return "A+"
                        elif energy_class == "APLUSPLUS":
                            return "A++"
                        else:
                            return energy_class
            
            # Fallback: Look for EPC patterns in text
            text = soup.get_text()
            epc_patterns = [
                r'EPC[:\s]*([A-G][+]*)',
                r'Energy[:\s]*([A-G][+]*)',
                r'([A-G][+]{0,2})\s*(?:energy|EPC)',
            ]
            
            for pattern in epc_patterns:
                epc_match = re.search(pattern, text, re.IGNORECASE)
                if epc_match:
                    return epc_match.group(1).upper()
        except Exception:
            pass
        return None
    
    def _extract_property_type_requests(self, soup) -> Optional[str]:
        """Extract property type using BeautifulSoup."""
        try:
            text = soup.get_text().lower()
            if 'apartment' in text or 'flat' in text:
                return 'apartment'
            elif 'house' in text:
                return 'house'
        except Exception:
            pass
        return None
    
    def _extract_bedrooms_requests(self, soup) -> Optional[str]:
        """Extract bedrooms using BeautifulSoup."""
        try:
            text = soup.get_text()
            bedroom_patterns = [
                r'(\d+)\s*bedroom',
                r'bedroom[s]?\s*[:]*\s*(\d+)',
                r'(\d+)\s*bed[s]?\b'
            ]
            
            for pattern in bedroom_patterns:
                bedroom_match = re.search(pattern, text, re.IGNORECASE)
                if bedroom_match:
                    return bedroom_match.group(1)
        except Exception:
            pass
        return None
    
    def _extract_construction_year_requests(self, soup) -> Optional[str]:
        """Extract construction year using BeautifulSoup."""
        try:
            text = soup.get_text()
            year_match = re.search(r'(?:built|construction|year).*?(\b(?:19|20)\d{2}\b)', text, re.IGNORECASE)
            if year_match:
                return year_match.group(1)
        except Exception:
            pass
        return None
    
    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract property ID from URL."""
        try:
            match = re.search(r'/classified/[^/]+/[^/]+/[^/]+/[^/]+/(\d+)', url)
            if match:
                return match.group(1)
        except:
            pass
        return None
    
    def _check_for_captcha(self, driver) -> bool:
        """Check if current page contains an active CAPTCHA challenge."""
        try:
            title = driver.title.lower()
            if "just a moment" in title or "captcha" in title:
                return True

            captcha_iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in captcha_iframes:
                src = iframe.get_attribute("src") or ""
                if "captcha-delivery.com" in src or "geo.captcha" in src:
                    return True

            return False
        except Exception:
            return False
    
    def _apply_advanced_stealth_mode(self, driver):
        """Apply advanced stealth techniques to avoid detection."""
        if _UC_AVAILABLE and isinstance(driver, uc.Chrome):
            return
        try:
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
                
                // Hide automation indicators
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
                
                // Override chrome property
                window.chrome = {
                    runtime: {},
                };
                
                // Mock realistic hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4,
                });
            """)
            
            # Set more realistic headers using CDP
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
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                }
            })
            
            # Additional stealth measures
            driver.execute_script("""
                // Remove webdriver traces
                delete window.webdriver;
                delete window.domAutomation;
                delete window.domAutomationController;
                delete window._phantom;
                delete window.__phantom;
                delete window.callPhantom;
                
                // Mock realistic screen properties
                Object.defineProperty(screen, 'availWidth', {get: () => 1920});
                Object.defineProperty(screen, 'availHeight', {get: () => 1040});
                Object.defineProperty(screen, 'width', {get: () => 1920});
                Object.defineProperty(screen, 'height', {get: () => 1080});
            """)
            
        except Exception as e:
            # Suppress detailed error - stealth mode is optional
            pass
    
    def _wait_for_page_load_with_captcha_check(self, driver, timeout=15):
        """Wait for page to load while checking for CAPTCHA."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._check_for_captcha(driver):
                print("   ⚠ CAPTCHA detected during page load")
                return False
                
            try:
                # Check if page has loaded
                if driver.execute_script("return document.readyState") == "complete":
                    return True
            except:
                pass
                
            time.sleep(1)
            
        return True
