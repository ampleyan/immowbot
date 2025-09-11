"""
Zimmo.be scraper - specialized scraper for Zimmo real estate platform.
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


class ZimmoScraper(BasePropertyScraper):
    """Scraper for Zimmo.be - Belgian real estate platform."""
    
    def __init__(self):
        super().__init__("Zimmo", "https://www.zimmo.be")
    
    def _build_search_url(self, max_price: Optional[int] = None, min_surface: Optional[int] = None,
                         epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None) -> str:
        """Build Zimmo search URL with filters using their search endpoint."""
        # Use Zimmo's search endpoint format
        base_search_url = "https://www.zimmo.be/nl/zoeken/"
        
        # If no filters provided, use basic search
        if not any([max_price, min_surface, epc_scores, postal_codes]):
            return "https://www.zimmo.be/nl/te-koop"
        
        # For filtered searches, use the provided example format
        # This is a simplified approach - for full implementation, would need to build the JSON filter
        # For now, fallback to basic search with URL parameters as a starting point
        basic_url = "https://www.zimmo.be/nl/te-koop"
        params = {}
        
        if max_price:
            params['price_max'] = str(max_price)
        
        if min_surface:
            params['surface_min'] = str(min_surface)
        
        if postal_codes:
            # Zimmo uses postal codes in search
            clean_codes = []
            for code in postal_codes:
                code = code.replace('BE-', '').strip()
                if code.isdigit() and len(code) == 4:
                    clean_codes.append(code)
            if clean_codes:
                params['postcode'] = ','.join(clean_codes)
        
        if epc_scores:
            # Convert EPC scores to Zimmo format
            epc_mapping = {
                'A++': 'A_PLUS_PLUS', 'A+': 'A_PLUS', 'A': 'A',
                'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F', 'G': 'G'
            }
            clean_scores = []
            for score in epc_scores:
                score = score.replace('BE-', '').strip()
                if score in epc_mapping:
                    clean_scores.append(epc_mapping[score])
            if clean_scores:
                params['energy'] = ','.join(clean_scores)
        
        # Build URL with parameters
        if params:
            return f"{basic_url}?{urlencode(params)}"
        else:
            return basic_url
    
    def scrape_with_filters(self, max_price: Optional[int] = None, min_surface: Optional[int] = None, 
                          epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None, 
                          max_pages: int = 5) -> List[Dict]:
        """Scrape Zimmo with filters."""
        search_url = self._build_search_url(max_price, min_surface, epc_scores, postal_codes)
        print(f"🌐 Scraping Zimmo with URL: {search_url}")
        
        return self.scrape_from_url(search_url, max_pages)
    
    def scrape_from_url(self, search_url: str, max_pages: int = 5) -> List[Dict]:
        """Scrape Zimmo from a specific search URL."""
        properties = []
        driver = None
        
        try:
            # Set up Chrome driver - Zimmo may need JavaScript
            driver = self._setup_chrome_driver()
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"🚀 Starting Zimmo scraping for {max_pages} pages...")
            
            for page in range(1, max_pages + 1):
                print(f"\n📄 Scraping Zimmo page {page}/{max_pages}...")
                
                # Build page URL - Zimmo pagination patterns
                if page == 1:
                    page_url = search_url
                else:
                    separator = '&' if '?' in search_url else '?'
                    page_url = f"{search_url}{separator}page={page}"
                
                print(f"   URL: {page_url}")
                driver.get(page_url)
                
                # Wait for content to load
                try:
                    WebDriverWait(driver, 15).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".property-card")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='property']")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".listing-item")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='Property']"))
                        )
                    )
                    time.sleep(2)
                except TimeoutException:
                    print(f"⏱️  Timeout waiting for property cards on page {page}")
                    pass
                
                # Extract property URLs from this page
                property_links = self._extract_property_links(driver)
                
                if not property_links:
                    print(f"   No properties found on page {page}")
                    # Check if we've reached the end
                    page_source = driver.page_source.lower()
                    if "geen resultaten" in page_source or "no results" in page_source or "geen woningen" in page_source:
                        print(f"   Reached end of results on page {page}")
                        break
                    continue
                
                print(f"   Found {len(property_links)} property URLs on page {page}")
                
                # Scrape individual properties
                for i, property_url in enumerate(property_links, 1):
                    # Make URL absolute if needed
                    if property_url.startswith('/'):
                        property_url = f"https://www.zimmo.be{property_url}"
                    
                    if self.is_property_already_scraped(property_url):
                        print(f"   ⏭️  [{i}/{len(property_links)}] Skipping already scraped property")
                        continue
                    
                    print(f"   [{i}/{len(property_links)}] Scraping: {property_url}")
                    
                    property_data = self._scrape_property_details(property_url, driver)
                    if property_data:
                        # Normalize the data using base class method
                        normalized_data = self._normalize_property_data(property_data)
                        
                        self.properties.append(normalized_data)
                        properties.append(normalized_data)
                        
                        print(f"   ✅ Scraped: {normalized_data.get('name', 'N/A')} - €{normalized_data.get('price', 'N/A'):,.0f}")
                        
                        # Add to existing properties to avoid re-scraping
                        self.existing_properties.add(property_url)
                    else:
                        print(f"   ❌ Failed to scrape property")
                    
                    time.sleep(3)  # Be respectful with requests
                
                time.sleep(5)  # Delay between pages
        
        finally:
            if driver:
                driver.quit()
        
        # Print summary
        successfully_scraped = len(properties)
        print(f"\n🎉 Zimmo Scraping Summary:")
        print(f"   ✅ Successfully scraped: {successfully_scraped}")
        if successfully_scraped > 0:
            print(f"   🏠 Average price: €{sum(p.get('price', 0) for p in properties) / len(properties):,.0f}")
        
        # Auto-export to JSON
        if properties:
            self.export_to_json()
        
        return properties
    
    def _extract_property_links(self, driver) -> List[str]:
        """Extract property links from Zimmo search results page."""
        property_links = []
        
        # Multiple selectors to try for Zimmo property cards
        selectors = [
            ".property-card a",
            "[data-testid='property'] a",
            ".listing-item a",
            "[class*='Property'] a",
            "a[href*='/te-koop/']",
            "a[href*='/property/']",
            "a[href*='/woning/']"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    if href and any(keyword in href for keyword in ['/te-koop/', '/property/', '/woning/']):
                        property_links.append(href)
                
                if property_links:
                    break  # Found some links with this selector
                    
            except Exception as e:
                print(f"   Error with selector {selector}: {e}")
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in property_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        return unique_links
    
    def _scrape_property_details(self, property_url: str, driver=None) -> Optional[Dict]:
        """Scrape detailed information for a single Zimmo property."""
        if not driver:
            print("   Warning: No driver provided to _scrape_property_details")
            return None
        
        try:
            print(f"   Accessing Zimmo property: {property_url}")
            driver.get(property_url)
            
            # Wait for content to load
            try:
                WebDriverWait(driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".property-price")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='price']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".property-header"))
                    )
                )
                time.sleep(2)
            except TimeoutException:
                print("   ⚠ Timeout waiting for property content")
            
            # Extract property data using BeautifulSoup
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract basic property information
            property_data = self._extract_zimmo_data(soup, property_url)
            
            if not property_data:
                print("   ❌ Could not extract property data")
                return None
            
            return property_data
                
        except Exception as e:
            print(f"   Error scraping Zimmo property: {e}")
            return None
    
    def _extract_zimmo_data(self, soup: BeautifulSoup, property_url: str) -> Optional[Dict]:
        """Extract property data from Zimmo HTML using BeautifulSoup."""
        try:
            # Extract price
            price = 0
            price_selectors = [
                ".property-price",
                "[class*='price']",
                ".price",
                "[data-testid='price']"
            ]
            
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = self._extract_price_from_text(price_text)
                    if price > 0:
                        break
            
            # Also try to find price in page text using regex
            if price == 0:
                page_text = soup.get_text()
                price_match = re.search(r'€\s*(\d{1,3}(?:[.,]\d{3})*)', page_text)
                if price_match:
                    price_str = price_match.group(1).replace('.', '').replace(',', '')
                    try:
                        price = float(price_str)
                    except ValueError:
                        pass
            
            # Extract location/address
            location = ""
            location_selectors = [
                ".property-address",
                "[class*='address']", 
                ".address",
                "[data-testid='address']",
                "h1",
                ".property-title"
            ]
            
            for selector in location_selectors:
                location_elem = soup.select_one(selector)
                if location_elem:
                    location = location_elem.get_text(strip=True)
                    if location and len(location) > 5:
                        break
            
            # Extract surface area
            surface_area = None
            surface_keywords = ["oppervlakte", "surface", "m²", "m2", "vierkante"]
            
            # Look for surface area in various elements
            all_text = soup.get_text()
            surface_patterns = [
                r'(\d+)\s*m[²2]',
                r'oppervlakte[:\s]*(\d+)',
                r'surface[:\s]*(\d+)',
                r'(\d+)\s*vierkante\s*meter'
            ]
            
            for pattern in surface_patterns:
                surface_match = re.search(pattern, all_text, re.IGNORECASE)
                if surface_match:
                    try:
                        surface_area = int(surface_match.group(1))
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Extract bedrooms
            bedrooms = None
            bedroom_patterns = [
                r'(\d+)\s*slaapkamer',
                r'(\d+)\s*bedroom',
                r'(\d+)\s*kamer'
            ]
            
            for pattern in bedroom_patterns:
                bedroom_match = re.search(pattern, all_text, re.IGNORECASE)
                if bedroom_match:
                    try:
                        bedrooms = int(bedroom_match.group(1))
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Extract property type
            property_type = "unknown"
            page_text_lower = all_text.lower()
            
            type_keywords = {
                "appartement": "apartment",
                "apartment": "apartment", 
                "huis": "house",
                "house": "house",
                "villa": "house",
                "studio": "studio",
                "penthouse": "apartment"
            }
            
            for keyword, normalized_type in type_keywords.items():
                if keyword in page_text_lower:
                    property_type = normalized_type
                    break
            
            # Extract postcode from location
            postcode = ""
            if location:
                postcode_match = re.search(r'\b(\d{4})\b', location)
                if postcode_match:
                    postcode = postcode_match.group(1)
            
            # Extract EPC score
            epc_score = ""
            epc_patterns = [
                r'EPC[:\s]*([A-G][+]*)',
                r'energie[:\s]*([A-G][+]*)',
                r'energy[:\s]*([A-G][+]*)'
            ]
            
            for pattern in epc_patterns:
                epc_match = re.search(pattern, all_text, re.IGNORECASE)
                if epc_match:
                    epc_score = epc_match.group(1).upper()
                    break
            
            # Extract description
            description = ""
            description_selectors = [
                ".property-description",
                "[class*='description']", 
                ".description",
                "[data-testid='description']",
                ".property-text"
            ]
            
            for selector in description_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    if len(description) > 50:
                        break
            
            # Build property data dictionary
            property_data = {
                'url': property_url,
                'name': location,
                'price': price,
                'location': location,
                'postcode': postcode,
                'property_type': property_type,
                'surface_area': surface_area,
                'bedrooms': bedrooms,
                'epc_score': epc_score,
                'description': description,
                'id': self._extract_id_from_url(property_url),
                'source': 'zimmo'
            }
            
            # Only return if we have at least price and location
            if price > 0 and location:
                return property_data
            else:
                print(f"   ⚠ Insufficient data: price={price}, location='{location}'")
                return None
                
        except Exception as e:
            print(f"   Error extracting Zimmo data: {e}")
            return None
    
    def _extract_price_from_text(self, price_text: str) -> float:
        """Extract numeric price from text."""
        if not price_text:
            return 0
        
        # Remove currency symbols and normalize
        clean_text = price_text.replace('€', '').replace(' ', '')
        
        # Handle different number formats (123.456 or 123,456)
        price_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)', clean_text)
        if price_match:
            try:
                price_str = price_match.group(1).replace('.', '').replace(',', '')
                return float(price_str)
            except ValueError:
                pass
        
        return 0
    
    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract property ID from Zimmo URL."""
        # Try common ID patterns in URLs
        id_patterns = [
            r'/(\d+)/?$',  # ID at end of URL
            r'/property/(\d+)',
            r'/woning/(\d+)',
            r'/te-koop/[^/]+/(\d+)'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Fallback - use last part of URL path
        parts = url.rstrip('/').split('/')
        if parts:
            return parts[-1]
        
        return None
    
    def _extract_property_urls(self, page_source: str, base_url: str = None) -> List[str]:
        """Extract property URLs from Zimmo search results page."""
        # This method is used by the base class but we handle URL extraction in scrape_from_url
        return []