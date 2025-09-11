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
import requests


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
                          max_pages: int = 5) -> List[Dict]:
        """Scrape Immoweb with filters."""
        search_url = self._build_search_url(max_price, min_surface, epc_scores, postal_codes)
        print(f"🌐 Scraping Immoweb with URL: {search_url}")
        
        return self.scrape_from_url(search_url, max_pages)
    
    def scrape_from_url(self, search_url: str, max_pages: int = 5) -> List[Dict]:
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
            
            # Enhanced anti-detection for DataDome CAPTCHA bypass
            self._apply_advanced_stealth_mode(driver)
            
            # Visit homepage first to establish session and get cookies
            print("   🏠 Visiting homepage first to establish session...")
            driver.get("https://www.immoweb.be")
            time.sleep(3)
            
            # Check for CAPTCHA on homepage
            if self._check_for_captcha(driver):
                print("   ⚠ CAPTCHA detected on homepage - waiting and retrying...")
                time.sleep(10)
                driver.refresh()
                time.sleep(5)
                
                if self._check_for_captcha(driver):
                    print("   ❌ CAPTCHA still present - scraping may be limited")
                    # Continue anyway - sometimes search pages work even if homepage has CAPTCHA
            
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
                        print(f"   ✅ Scraped: {normalized_data.get('name', 'N/A')} - €{normalized_data.get('price', 'N/A'):,.0f}")
                        
                        # Add to existing properties to avoid re-scraping in same session
                        if normalized_data.get('id'):
                            self.existing_properties.add(str(normalized_data.get('id')))
                        self.existing_properties.add(property_url)
                    else:
                        print(f"   ❌ Failed to scrape property")
                        
                    time.sleep(8)  # Longer delays to avoid CAPTCHA

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
                    property_data = av_items[0]
                    property_data['street'] = self._extract_location(driver)
                    
                    # Try to get additional contact information
                    try:
                        classified_data = driver.execute_script("return window.classified || {};")
                    except Exception as e:
                        classified_data = {}
                else:
                    # Fallback: Parse from classified data in HTML
                    print("   ⚠ JavaScript data not available, using HTML parsing fallback")
                    response = self.session.get(property_url, timeout=10)
                    
                    match = re.search(r'window\.classified\s*=\s*({.*?});', response.text, re.DOTALL)
                    if match:
                        try:
                            json_str = match.group(1)
                            classified_data = json.loads(json_str)
                            
                            # Extract data from classified structure
                            prop = classified_data.get('property', {})
                            location = prop.get('location', {})
                            price_info = classified_data.get('price', {})
                            transaction = classified_data.get('transaction', {})
                            certificates = transaction.get('certificates', {})
                            
                            # Build property_data in expected format
                            property_data = {
                                'id': classified_data.get('id'),
                                'price': price_info.get('mainValue', 0),
                                'street': f"{location.get('street', '')} {location.get('number', '')}".strip(),
                                'city': location.get('locality', ''),
                                'zip_code': location.get('postalCode', ''),
                                'subtype': prop.get('subtype', '').lower(),
                                'indoor_surface': prop.get('netHabitableSurface'),
                                'nb_bedrooms': prop.get('bedroomCount'),
                                'year_of_construction': prop.get('building', {}).get('constructionYear'),
                                'energy_certificate': certificates.get('epcScore'),
                                'latitude': location.get('latitude'),
                                'longitude': location.get('longitude'),
                                'description': (
                                    prop.get('alternativeDescriptions', {}).get('nl', '') or
                                    prop.get('description', '')
                                ),
                            }
                            
                            print("   ✓ Successfully extracted classified data from HTML")
                            
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"   ⚠ Failed to parse classified data: {e}")
                            return None
                    else:
                        print("   ❌ No property data found")
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
                    'epc_score': property_data.get('energy_certificate', ''),
                    'latitude': self._safe_float(property_data.get('latitude')),
                    'longitude': self._safe_float(property_data.get('longitude')),
                    'description': property_data.get('description', ''),
                    'source': 'immoweb',  # Source website identifier
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
    
    def _fallback_html_parsing(self, property_url: str, response) -> Dict:
        """Fallback method to parse property data from HTML when JavaScript data unavailable."""
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
            'street': self._extract_location_requests(soup),
            'city': '',
            'province': '',
            'latitude': None,
            'longitude': None,
            'description': ''
        }
        
        # Extract postcode from location
        if property_data['location']:
            postcode_match = re.search(r'\b(\d{4})\b', property_data['location'])
            if postcode_match:
                property_data['postcode'] = postcode_match.group(1)
        
        # Try to find description in HTML
        desc_element = soup.find('div', {'data-testid': 'description'}) or soup.find('div', class_='classified__description')
        if desc_element:
            property_data['description'] = desc_element.get_text(strip=True)
        
        print("   ✓ Basic HTML parsing completed")
        return property_data
    
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
        """Check if current page contains a CAPTCHA challenge."""
        try:
            page_source = driver.page_source.lower()
            
            # Check for DataDome CAPTCHA indicators
            captcha_indicators = [
                'datadome',
                'captcha-delivery.com',
                'geo.captcha-delivery.com',
                'ct.captcha-delivery.com',
                'data-cfasync="false"',
                'dd={',
                'iframe src="https://geo.captcha-delivery.com',
                'title="DataDome CAPTCHA"'
            ]
            
            for indicator in captcha_indicators:
                if indicator in page_source:
                    return True
                    
            # Check for CAPTCHA iframes
            captcha_iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in captcha_iframes:
                src = iframe.get_attribute("src") or ""
                title = iframe.get_attribute("title") or ""
                if "captcha" in src.lower() or "captcha" in title.lower():
                    return True
                    
            return False
        except Exception:
            return False
    
    def _apply_advanced_stealth_mode(self, driver):
        """Apply advanced stealth techniques to avoid detection."""
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
            print(f"   ⚠ Warning: Could not apply full stealth mode: {e}")
    
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