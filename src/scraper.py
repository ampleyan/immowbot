"""
Web scraper for Immoweb.be property listings.
"""
import json
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs
from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import requests
from bs4 import BeautifulSoup


class ImmowebScraper:
    """Scraper for Immoweb.be property listings."""
    
    def __init__(self):
        self.base_url = "https://www.immoweb.be"
        self.session = requests.Session()
        self.properties_url = []
        self.properties = []  # Class attribute to store all scraped properties
        # Better headers to avoid detection
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
        
    def _setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Try to get and install the chrome driver
            driver_path = ChromeDriverManager().install()
            print(f"Chrome driver path: {driver_path}")
            
            # Check if the driver file is valid
            import os
            if not os.path.exists(driver_path) or os.path.getsize(driver_path) < 1000:
                print("Chrome driver appears to be corrupted, trying to reinstall...")
                # Clear the driver cache and try again
                ChromeDriverManager().install()
                driver_path = ChromeDriverManager().install()
            # Use the dynamically installed driver path
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            return driver
        except Exception as e:
            print(f"Error setting up Chrome WebDriver: {e}")
            print("Falling back to requests-based scraping...")
            raise e
    
    def scrape_from_url(self, search_url: str, max_pages: int = 5) -> List[Dict]:
        """Scrape properties from a given Immoweb search URL."""
        properties = []
        
        # Try Selenium first, fall back to requests if it fails
        try:
            driver = self._setup_driver()
            return self._scrape_with_selenium(search_url, max_pages, driver)
        except Exception as e:
            print(f"Selenium scraping failed: {e}")
            print("Falling back to requests-based scraping...")
            return self._scrape_with_requests(search_url, max_pages)
    
    def _scrape_with_selenium(self, search_url: str, max_pages: int, driver: webdriver.Chrome) -> List[Dict]:
        """Scrape using Selenium WebDriver."""
        properties = []
        
        try:
            for page in range(1, max_pages + 1):
                # Update page number in URL
                url = self._update_page_number(search_url, page)
                print(f"Scraping page {page}: {url}")
                
                driver.get(url)
                time.sleep(3)  # Wait for page to load
                
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
                
                for card in property_cards:
                    try:
                        # Get property URL using the correct selector for the title link
                        self.properties_url.append(card.get_attribute("href"))

                    except Exception as e:
                        print(f"Error extracting property card: {e}")
                        continue

                time.sleep(5)  # Be respectful with requests

                for property_url in self.properties_url:
                    if property_url and "/classified/" in property_url:
                        # URL is already full, no need for urljoin
                        property_data = self._scrape_property_details(property_url, driver)
                        if property_data:
                            self.properties.append(property_data)
                            properties.append(property_data)  # Keep for return value
                            print(
                                f"Scraped property: {property_data.get('name', 'N/A')} - €{property_data.get('price', 'N/A')}")
                        time.sleep(5)  # Be respectful with requests


        finally:
            driver.quit()
        
        return properties
    
    def _scrape_with_requests(self, search_url: str, max_pages: int = 5) -> List[Dict]:
        """Fallback scraping using requests and BeautifulSoup."""
        properties = []
        
        print("Using requests-based scraping (limited functionality)")
        print("Note: This method may have limited success due to anti-bot measures")
        
        for page in range(1, max_pages + 1):
            url = self._update_page_number(search_url, page)
            print(f"Scraping page {page}: {url}")
            
            try:
                # Visit homepage first to get cookies
                if page == 1:
                    print("Getting initial cookies...")
                    home_response = self.session.get(self.base_url, timeout=10)
                    time.sleep(2)
                
                # Add more realistic headers for this request
                headers = {
                    'Referer': self.base_url if page == 1 else self._update_page_number(search_url, page-1),
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin' if page > 1 else 'none',
                    'Sec-Fetch-User': '?1'
                }
                
                response = self.session.get(url, headers=headers, timeout=15)
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 403:
                    print(f"Access forbidden (403) - website is blocking requests")
                    print("Try using a VPN or accessing the site manually first")
                    break
                elif response.status_code != 200:
                    print(f"Failed to fetch page {page}: HTTP {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for the main search results list
                search_results = soup.find('ul', {'id': 'main-content', 'class': 'search-results__list'})
                found_properties = 0
                
                if search_results:
                    # Find all property cards
                    property_cards = search_results.find_all('li', class_='search-results__item')
                    
                    for card in property_cards:
                        # Find the title link within each card
                        link = card.find('a', class_='card__title-link')
                        if link and link.get('href'):
                            property_url = link.get('href')
                            
                            # Ensure full URL
                            if not property_url.startswith('http'):
                                property_url = urljoin(self.base_url, property_url)
                            
                            property_data = self._scrape_property_details_requests(property_url)
                            if property_data:
                                self.properties.append(property_data)
                                properties.append(property_data)  # Keep for return value
                                found_properties += 1
                                print(f"Scraped property: {property_data.get('name', 'N/A')} - €{property_data.get('price', 'N/A')}")
                else:
                    # Fallback: look for any classified links if main structure not found
                    property_links = soup.find_all('a', class_='card__title-link', href=True)

                    for link in property_links:
                        href = link.get('href')
                        if href and '/classified/' in href:
                            if not href.startswith('http'):
                                property_url = urljoin(self.base_url, href)
                            else:
                                property_url = href
                            
                            property_data = self._scrape_property_details_requests(property_url)
                            if property_data:
                                self.properties.append(property_data)
                                properties.append(property_data)  # Keep for return value
                                found_properties += 1
                                print(f"Scraped property: {property_data.get('name', 'N/A')} - €{property_data.get('price', 'N/A')}")
                                if found_properties >= 10:  # Limit fallback results
                                    break
                
                if found_properties == 0:
                    print(f"No properties found on page {page}")
                    break
                
                time.sleep(3)  # Be respectful with requests
                
            except Exception as e:
                print(f"Error scraping page {page}: {e}")
                continue
        
        return properties
    
    def _update_page_number(self, url: str, page: int) -> str:
        """Update the page number in a search URL."""
        if "page=" in url:
            return re.sub(r'page=\d+', f'page={page}', url)
        else:
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}page={page}"
    
    def _scrape_property_details(self, property_url: str, driver: webdriver.Chrome) -> Optional[Dict]:
        """Scrape detailed information from a single property page."""
        try:
            driver.get(property_url)
            time.sleep(2)
            html_content = driver.page_source

            # Wait for the main content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )

            try:
                # Try to get av_items directly from JavaScript context
                av_items = driver.execute_script("return av_items;")
                if not av_items or not isinstance(av_items, list):
                    raise ValueError("Could not find av_items data")

                property_data = av_items[0]
                
                # Try to get additional contact information from .classified object
                classified_data = {}
                try:
                    classified_data = driver.execute_script("return window.classified || {};")
                except Exception as e:
                    print(f"Could not extract classified data: {e}")
                    classified_data = {}

                # Handle price range
                price_str = property_data.get('price', '0')
                if ' - ' in price_str:
                    # For price ranges, take the lower bound
                    price = float(price_str.split(' - ')[0].replace(',', ''))
                else:
                    price = float(price_str) if price_str else 0

                # Handle empty string values for numeric fields
                def safe_int(value):
                    return int(value) if value and value.strip() else None

                def safe_float(value):
                    return float(value) if value and value.strip() else None

                def safe_bool(value):
                    if isinstance(value, str):
                        return value.lower() in ('true', '1', 'yes')
                    return bool(value) if value is not None else None

                def parse_coordinates(geolocation_str):
                    """Parse 'lng,lat' string into tuple (lat, lng)"""
                    if geolocation_str and ',' in geolocation_str:
                        try:
                            lng, lat = geolocation_str.split(',')
                            return (float(lat.strip()), float(lng.strip()))
                        except (ValueError, IndexError):
                            pass
                    return None

                # Create property name from address components
                def create_property_name(data, classified):
                    components = []
                    
                    # Get property type and city
                    prop_type = data.get('subtype', '').title()
                    city = data.get('city', '')
                    postcode = data.get('zip_code', '')
                    
                    if prop_type:
                        components.append(prop_type)
                    if city:
                        components.append(f"in {city}")
                    if postcode:
                        components.append(postcode)
                    
                    return ' '.join(components) if components else f"Property {data.get('id', '')}"

                # Extract contact information from classified object
                def extract_contact_info(classified):
                    contact_info = {}
                    customers = classified.get('customers', [])
                    if customers:
                        customer = customers[0]  # Get primary contact
                        contact_info = {
                            'agent_name': customer.get('name', ''),
                            'agent_email': customer.get('email', ''),
                            'agent_phone': customer.get('phoneNumber', ''),
                            'agent_mobile': customer.get('mobileNumber', ''),
                            'agent_website': customer.get('website', ''),
                            'agent_type': customer.get('type', ''),
                            'agent_logo': customer.get('logoUrl', ''),
                            'is_owner': customer.get('isOwner', False),
                        }
                        
                        # Add agent location if available
                        if 'location' in customer:
                            agent_location = customer['location']
                            contact_info.update({
                                'agent_address': f"{agent_location.get('street', '')} {agent_location.get('number', '')}".strip(),
                                'agent_city': agent_location.get('locality', ''),
                                'agent_postcode': agent_location.get('postalCode', ''),
                                'agent_province': agent_location.get('province', ''),
                            })
                    
                    return contact_info

                # Enhanced property details with all available fields
                # Using field names expected by analyzer while preserving enhanced data
                contact_info = extract_contact_info(classified_data)
                property_name = create_property_name(property_data, classified_data)
                
                # Parse coordinates once to avoid multiple function calls
                coords = parse_coordinates(property_data.get('geolocation'))
                
                details = {
                    # Core Property Information (Analyzer Compatible)
                    'name': property_name,  # Property name based on address
                    'url': property_url,
                    'id': property_data.get('id'),
                    'price': price,
                    'surface_area': safe_float(property_data.get('indoor_surface', '')),  # Analyzer expects this name
                    'bedrooms': safe_int(property_data.get('nb_bedrooms', '')),
                    'property_type': property_data.get('subtype'),
                    'construction_year': safe_int(property_data.get('year_of_construction', '')),  # Analyzer expects this name
                    'postcode': property_data.get('zip_code'),
                    'epc_score': property_data.get('energy_certificate'),  # Analyzer expects this name
                    'location': f"{property_data.get('city', '')} {property_data.get('zip_code', '')}".strip(),
                    
                    # Enhanced Fields - Additional Data
                    'currency': property_data.get('currency', 'eur'),
                    'rooms': safe_int(property_data.get('nb_rooms', '')),
                    'land_surface': safe_float(property_data.get('land_surface', '')),
                    'outdoor_surface': safe_float(property_data.get('outdoor_surface', '')),
                    'energy_type': property_data.get('energy'),
                    
                    # Location Details (Enhanced)
                    'city': property_data.get('city'),
                    'province': property_data.get('province'),
                    'country': property_data.get('country', 'Belgium'),
                    'coordinates': coords,
                    'latitude': coords[0] if coords else None,
                    'longitude': coords[1] if coords else None,
                    
                    # Property Features & Amenities
                    'building_state': property_data.get('building_state'),
                    'kitchen_type': property_data.get('kitchen_type'),
                    'outdoor_terrace': safe_bool(property_data.get('outdoor_terrace_exists')),
                    'parking': safe_bool(property_data.get('parking')),
                    
                    # Property Classification
                    'estate_type': property_data.get('estate_type'),
                    'distribution_type': property_data.get('distribution_type'),
                    'distribution_subtype': property_data.get('distribution_subtype'),
                    'product_type': property_data.get('product_type'),
                    
                    # Media & Marketing
                    'num_pictures': safe_int(property_data.get('nb_picture', '')),
                    'rating': property_data.get('rating'),
                    
                    # Agent/Seller Information
                    'client_id': property_data.get('client_id'),
                    'client_type': property_data.get('client_type'),
                    'publication_id': property_data.get('publication_id', 'IWB'),
                }
                
                # Add contact information to details
                details.update(contact_info)

                return details


            except (json.JSONDecodeError, KeyError, ValueError, Exception) as e:
                raise ValueError(f"Failed to parse property data: {str(e)}")

            # return property_data
            
        except Exception as e:
            print(f"Error scraping property details from {property_url}: {e}")
            return None
    
    def _scrape_property_details_requests(self, property_url: str) -> Optional[Dict]:
        """Scrape property details using requests (fallback method)."""
        try:
            response = self.session.get(property_url, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            property_data = {
                'url': property_url,
                'price': self._extract_price_requests(soup),
                'location': self._extract_location_requests(soup),
                'postcode': None,  # Will be extracted from location
                'surface_area': self._extract_surface_area_requests(soup),
                'epc_score': self._extract_epc_score_requests(soup),
                'property_type': self._extract_property_type_requests(soup),
                'bedrooms': self._extract_bedrooms_requests(soup),
                'construction_year': self._extract_construction_year_requests(soup),
            }
            
            # Extract postcode from location
            if property_data['location']:
                postcode_match = re.search(r'\b(\d{4})\b', property_data['location'])
                if postcode_match:
                    property_data['postcode'] = postcode_match.group(1)
            
            return property_data
            
        except Exception as e:
            print(f"Error scraping property details from {property_url}: {e}")
            return None
    
    def _extract_price_requests(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract price using requests method."""
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
    
    def _extract_location_requests(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract location using requests method."""
        try:
            # Look for location in breadcrumb or title
            location_selectors = [
                '[data-testid="breadcrumb"] span:last-child',
                'h1',
                'h2',
                '.classified__title'
            ]
            
            for selector in location_selectors:
                location_element = soup.select_one(selector)
                if location_element:
                    return location_element.get_text(strip=True)
        except Exception:
            pass
        return None
    
    def _extract_surface_area_requests(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract surface area using requests method."""
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
    
    def _extract_epc_score_requests(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract EPC score using requests method."""
        try:
            # Look for EPC image with class "classified-table__picture"
            epc_imgs = soup.find_all('img', class_='classified-table__picture')
            
            for img in epc_imgs:
                src = img.get('src', '')
                if 'epc/pics/peb' in src:
                    # Extract energy class from filename (letter before .png)
                    import re
                    match = re.search(r'/([a-g][+]*?)\.png$', src, re.IGNORECASE)
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
    
    def _extract_property_type_requests(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property type using requests method."""
        try:
            text = soup.get_text().lower()
            if 'apartment' in text or 'flat' in text:
                return 'Apartment'
            elif 'house' in text:
                return 'House'
        except Exception:
            pass
        return None
    
    def _extract_bedrooms_requests(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract bedrooms using requests method."""
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
    
    def _extract_construction_year_requests(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract construction year using requests method."""
        try:
            text = soup.get_text()
            year_match = re.search(r'(?:built|construction|year).*?(\b(?:19|20)\d{2}\b)', text, re.IGNORECASE)
            if year_match:
                return year_match.group(1)
        except Exception:
            pass
        return None
    
    def _extract_price(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract property price."""
        try:
            # Look for price in various possible selectors based on the search results structure
            price_selectors =  ['.classified__price']
            
            for selector in price_selectors:
                try:
                    price_element = driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_element.text.strip()
                    # Extract numeric price
                    price_match = re.search(r'€\s*([\d,]+)', price_text)
                    if price_match:
                        return price_match.group(1).replace(',', '')
                    return price_text
                except:
                    continue
            return None
        except:
            return None
    
    def _extract_location(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract property location."""
        try:
            # Look for location in various possible selectors
            location_selectors = [
              '.classified__information--address-row'
            ]
            
            for selector in location_selectors:
                try:
                    location_element = driver.find_element(By.CSS_SELECTOR, selector)
                    return location_element.text.strip()
                except:
                    continue
            return None
        except:
            return None
    
    def _extract_postcode(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract property postcode."""
        try:
            location_text = self._extract_location(driver) or ""
            postcode_match = re.search(r'\b(\d{4})\b', location_text)
            if postcode_match:
                return postcode_match.group(1)
        except:
            pass
        return None
    
    def _extract_surface_area(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract property surface area."""
        try:
            # Look for surface area in classified table or other selectors
            surface_selectors = [
                '.classified-table__data--surface',
                '[data-testid="surface-area"]'
            ]
            
            for selector in surface_selectors:
                try:
                    surface_element = driver.find_element(By.CSS_SELECTOR, selector)
                    surface_text = surface_element.text.strip()
                    # Extract numeric value before m²
                    surface_match = re.search(r'(\d+)', surface_text)
                    if surface_match:
                        return surface_match.group(1)
                except:
                    continue
            
            return None
        except:
            return None
    
    def _extract_epc_score(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract EPC energy score from image src attribute."""
        try:
            # Look for EPC image with class "classified-table__picture"
            epc_img_elements = driver.find_elements(By.CSS_SELECTOR, "img.classified-table__picture")
            
            for img in epc_img_elements:
                src = img.get_attribute("src")
                if src and "epc/pics/peb" in src:
                    # Extract energy class from filename (letter before .png)
                    # e.g., "https://media.immowebstatic.be/epc/pics/peb/fla/e.png" -> "E"
                    import re
                    match = re.search(r'/([a-g][+]*?)\.png$', src, re.IGNORECASE)
                    if match:
                        energy_class = match.group(1).upper()
                        # Handle A+ and A++ variants
                        if energy_class == "APLUS":
                            return "A+"
                        elif energy_class == "APLUSPLUS":
                            return "A++"
                        else:
                            return energy_class
            
            # Fallback: Look for EPC in table cells
            epc_elements = driver.find_elements(By.XPATH, "//th[contains(text(), 'EPC score')]/following-sibling::td")
            if epc_elements:
                return epc_elements[0].text.strip()
            
            return None
        except:
            return None
    
    def _extract_property_type(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract property type (house, apartment, etc.)."""
        try:
            # Look for property type in various selectors
            type_selectors = [
                '.classified__title h1',
                '.classified-table__data--property-type'
            ]
            
            for selector in type_selectors:
                try:
                    type_element = driver.find_element(By.CSS_SELECTOR, selector)
                    type_text = type_element.text.strip().lower()
                    if 'apartment' in type_text:
                        return 'Apartment'
                    elif 'house' in type_text or 'villa' in type_text:
                        return 'House'
                except:
                    continue
            
            return None
        except:
            return None
    
    def _extract_bedrooms(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract number of bedrooms."""
        try:
            # Look for bedrooms in various selectors
            bedroom_selectors = [
                '.classified-table__data--bedrooms',
                '[data-testid="bedrooms"]'
            ]
            
            for selector in bedroom_selectors:
                try:
                    bedroom_element = driver.find_element(By.CSS_SELECTOR, selector)
                    bedroom_text = bedroom_element.text.strip()
                    # Extract numeric value
                    bedroom_match = re.search(r'(\d+)', bedroom_text)
                    if bedroom_match:
                        return bedroom_match.group(1)
                except:
                    continue
            
            return None
        except:
            return None
    
    def _extract_construction_year(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract construction year."""
        try:
            # Look for construction year in various selectors
            year_selectors = [
                '.classified-table__data--construction-year',
                '[data-testid="construction-year"]'
            ]
            
            for selector in year_selectors:
                try:
                    year_element = driver.find_element(By.CSS_SELECTOR, selector)
                    year_text = year_element.text.strip()
                    # Extract 4-digit year
                    year_match = re.search(r'(\b(?:19|20)\d{2}\b)', year_text)
                    if year_match:
                        return year_match.group(1)
                except:
                    continue
            
            return None
        except:
            return None
    
    def scrape_with_filters(self, max_price: Optional[int] = None, min_surface: Optional[int] = None, 
                          epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None,
                          max_pages: int = 5) -> List[Dict]:
        """Scrape properties with specified filters."""
        # Build search URL with filters
        base_search_url = f"{self.base_url}/en/search/house-and-apartment/for-sale?countries=BE"
        
        if max_price:
            base_search_url += f"&maxPrice={max_price}"
        if min_surface:
            base_search_url += f"&minSurface={min_surface}"
        if epc_scores:
            epc_param = ",".join(epc_scores)
            base_search_url += f"&epcScores={epc_param}"
        if postal_codes:
            # Clean postal codes and ensure proper format
            cleaned_codes = []
            for code in postal_codes:
                code = code.strip()
                if not code.startswith('BE-'):
                    code = f"BE-{code}"
                cleaned_codes.append(code)
            postal_param = ",".join(cleaned_codes)
            base_search_url += f"&postalCodes={postal_param}"
        
        base_search_url += "&orderBy=relevance"
        
        return self.scrape_from_url(base_search_url, max_pages)
    
    def get_all_properties(self) -> List[Dict]:
        """Get all scraped properties from class attribute."""
        return self.properties
    
    def clear_properties(self):
        """Clear all stored properties."""
        self.properties.clear()
        self.properties_url.clear()
    
    def get_property_count(self) -> int:
        """Get total number of scraped properties."""
        return len(self.properties)
    
    def get_properties_with_contact_info(self) -> List[Dict]:
        """Get all properties that have contact information."""
        return [prop for prop in self.properties if prop.get('agent_name') or prop.get('agent_phone')]
    
    def export_properties_summary(self) -> Dict[str, Any]:
        """Export a summary of all scraped properties."""
        if not self.properties:
            return {"message": "No properties scraped yet"}
        
        total_properties = len(self.properties)
        properties_with_contact = len(self.get_properties_with_contact_info())
        
        # Price statistics
        prices = [p.get('price', 0) for p in self.properties if p.get('price')]
        price_stats = {}
        if prices:
            price_stats = {
                'min_price': min(prices),
                'max_price': max(prices),
                'avg_price': sum(prices) / len(prices),
                'total_value': sum(prices)
            }
        
        # Location distribution
        cities = {}
        for prop in self.properties:
            city = prop.get('city', 'Unknown')
            cities[city] = cities.get(city, 0) + 1
        
        return {
            'total_properties': total_properties,
            'properties_with_contact': properties_with_contact,
            'price_statistics': price_stats,
            'cities': cities,
            'sample_properties': self.properties[:3]  # First 3 as examples
        }