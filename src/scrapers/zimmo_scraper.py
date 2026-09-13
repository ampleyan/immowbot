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
from ..translator import PropertyTranslator


class ZimmoScraper(BasePropertyScraper):
    """Scraper for Zimmo.be - Belgian real estate platform."""
    
    def __init__(self):
        super().__init__("Zimmo", "https://www.zimmo.be")
        self.translator = PropertyTranslator()
    
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
    
    def scrape_with_filters(self, min_price: Optional[int] = None, max_price: Optional[int] = None, min_surface: Optional[int] = None,
                          epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None, 
                          max_pages: int = 5, on_listing=None, on_checked=None,
                          should_cancel=None) -> List[Dict]:
        """Scrape Zimmo with filters."""
        # search_url = self._build_search_url(max_price, min_surface, epc_scores, postal_codes)
        search_url = 'https://www.zimmo.be/nl/zoeken/?search=eyJmaWx0ZXIiOnsic3RhdHVzIjp7ImluIjpbIkZPUl9TQUxFIiwiVEFLRV9PVkVSIl19LCJwcmljZSI6eyJyYW5nZSI6eyJtYXgiOjM1MDAwMH0sInVua25vd24iOnRydWV9LCJmbG9vcnNwYWNlU3VyZmFjZSI6eyJyYW5nZSI6eyJtaW4iOjgwfSwidW5rbm93biI6dHJ1ZX0sImVuZXJneUxhYmVsIjp7ImluIjpbIkFfUExVU19QTFVTIiwiQV9QTFVTIiwiQSIsIkFfTUlOVVMiLCJCX1BMVVMiLCJCIiwiQl9NSU5VUyIsIkNfUExVUyIsIkMiLCJDX01JTlVTIl0sInVua25vd24iOnRydWV9LCJjYXRlZ29yeSI6eyJpbiI6WyJIT1VTRSIsIkFQQVJUTUVOVCJdfSwicGxhY2VJZCI6eyJpbiI6WzMyNzAsMzI3MSwzMjcyLDMyNjddfX19'
        print(f"🌐 Scraping Zimmo with URL: {search_url}")
        
        return self.scrape_from_url(search_url, max_pages, on_listing, on_checked, should_cancel)
    
    def scrape_from_url(self, search_url: str, max_pages: int = 10, on_listing=None,
                        on_checked=None, should_cancel=None) -> List[Dict]:
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
                    page_url = f"{search_url}{separator}p={page}"
                
                print(f"   URL: {page_url}")
                driver.get(page_url)
                
                # Wait for content to load
                try:
                    WebDriverWait(driver, 15).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".property-item" )),
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
                    if should_cancel and should_cancel():
                        break
                    # Make URL absolute if needed
                    if property_url.startswith('/'):
                        property_url = f"https://www.zimmo.be{property_url}"

                    if not self._postcode_allowed(property_url):
                        print(f"   ⏭️  [{i}/{len(property_links)}] Skipping postcode mismatch: {property_url}")
                        if on_checked:
                            on_checked()
                        continue
                    
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
                        if on_listing:
                            on_listing(normalized_data)
                        
                        print(f"   ✅ Scraped: {normalized_data.get('name', 'N/A')} - €{normalized_data.get('price', 'N/A'):,.0f}")
                        
                        # Add to existing properties to avoid re-scraping
                        self.existing_properties.add(property_url)
                    else:
                        print(f"   ❌ Failed to scrape property")
                    if on_checked:
                        on_checked()
                    if should_cancel and should_cancel():
                        break
                    time.sleep(3)  # Be respectful with requests
                if should_cancel and should_cancel():
                    break
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
            '.property-item_link',
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
                    href = element.get_attribute('href').split('?')[0]
                    if href and re.search(r'/(appartement|huis|woning|studio|nieuwbouwproject)/[A-Z0-9]{4,}', href):
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
    
    def _parse_ng_state(self, soup: BeautifulSoup, property_url: str):
        script = soup.find("script", {"id": "ng-state", "type": "application/json"})
        if not script:
            return None
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            return None
        code_match = re.search(r'/([A-Z0-9]{4,})/?$', property_url)
        if not code_match:
            return None
        code = code_match.group(1)
        key = f"LISTING_DETAIL_{code}"
        listing = data.get(key)
        if not listing:
            for k in data:
                if k.startswith("LISTING_DETAIL_"):
                    listing = data[k]
                    break
        if not listing:
            return None
        estate = listing.get("estate", {})
        cert = (estate.get("certificate") or {}).get("epcCertificate") or {}
        loc = estate.get("location") or {}
        coords = loc.get("coordinates") or {}
        surface_obj = estate.get("floorspaceSurface") or {}
        price_obj = estate.get("price") or {}
        layout = estate.get("layout") or []
        bedrooms = sum(1 for item in layout if isinstance(item, dict) and item.get("spaceType") == "BEDROOM")
        street = f"{loc.get('street', '')} {loc.get('streetNumber', '')}".strip()
        city = (loc.get("locality") or {}).get("en", "")
        postcode = loc.get("postalCode", "")
        location = f"{street}, {postcode} {city}".strip(", ")
        energy_label = cert.get("energyLabel", "")
        epc_score = self._normalize_epc_label(energy_label)
        url_lower = property_url.lower()
        if "/appartement" in url_lower:
            property_type = "apartment"
        elif "/huis" in url_lower or "/woning" in url_lower:
            property_type = "house"
        elif "/studio" in url_lower:
            property_type = "studio"
        else:
            property_type = "unknown"
        return {
            "id": listing.get("id", ""),
            "url": property_url,
            "name": location,
            "price": float(price_obj.get("value", 0)),
            "location": location,
            "postcode": postcode,
            "property_type": property_type,
            "surface_area": surface_obj.get("value"),
            "bedrooms": bedrooms or None,
            "bathrooms": estate.get("bathroomsCount"),
            "construction_year": estate.get("constructionYear"),
            "epc_score": epc_score,
            "latitude": coords.get("latitude"),
            "longitude": coords.get("longitude"),
            "_ng_state": True,
        }

    def _extract_zimmo_data(self, soup: BeautifulSoup, property_url: str) -> Optional[Dict]:
        try:
            ng = self._parse_ng_state(soup, property_url)
            if ng and ng.get("price", 0) > 0:
                description = ""
                desc_elem = soup.select_one('.section-description .description-block')
                if not desc_elem:
                    for sel in [".property-description", "[class*='description']", ".description"]:
                        desc_elem = soup.select_one(sel)
                        if desc_elem and len(desc_elem.get_text(strip=True)) > 50:
                            break
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                translation_result = self.translator.translate_property_description(description)
                ng["description"] = description
                ng["description_english"] = translation_result["translated"]
                ng["description_language"] = translation_result["detected_language"]
                ng["has_tenant"] = self._check_tenant_situation(description)
                ng["under_option"] = False
                ng["source"] = "zimmo"
                ng["data_source"] = "zimmo_ng_state"
                ng["all_property_details"] = {
                    "Surface": f"{ng['surface_area']}m²" if ng.get("surface_area") else None,
                    "Bedrooms": ng.get("bedrooms"),
                    "EPC score": ng.get("epc_score"),
                    "Construction year": ng.get("construction_year"),
                    "Property type": ng.get("property_type"),
                    "HAS_TENANT": "YES" if ng.get("has_tenant") else "No",
                    "Description Language": (ng.get("description_language") or "").upper(),
                    "Description (Original)": description,
                    "Description (English)": ng.get("description_english", ""),
                }
                return ng

            # Fallback: CSS selectors on the updated Zimmo HTML structure
            # Extract price from price-box or price-value sections
            price = 0

            # Try specific Zimmo price selectors first
            price_selectors = [
                ".price-value .feature-value",
                ".price-box .price-value",
                ".price-value", 
                ".feature-value",
                "[class*='price']"
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
            
            # Initialize data dictionary
            data = {}

            # Updated Zimmo HTML uses .feature_title / .feature_value (underscore)
            for feature_div in soup.select('.feature'):
                label_elem = feature_div.select_one('.feature_title')
                value_elem = feature_div.select_one('.feature_value')
                if not (label_elem and value_elem):
                    label_elem = feature_div.select_one('.feature-label')
                    value_elem = feature_div.select_one('.feature-value')
                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).lower()
                    value = value_elem.get_text(strip=True)
                    if 'adres' in label or 'address' in label:
                        data['location'] = value
                    elif 'prijs' in label or 'price' in label:
                        data['price_text'] = value
                    elif 'type' in label:
                        data['property_type'] = value
                    elif 'woonoppervlakte' in label or 'woonopp' in label:
                        data['surface_area_text'] = value
                    elif 'grondopp' in label:
                        data['terrain_area_text'] = value
                    elif 'slaapkamer' in label or 'bedroom' in label:
                        data['bedrooms_text'] = value
                    elif 'badkamer' in label or 'bathroom' in label:
                        data['bathrooms_text'] = value
                    elif 'bouwjaar' in label:
                        data['construction_year_text'] = value
                    elif 'epc-waarde' in label or 'epc waarde' in label:
                        pass  # kWh value — discard, label is in ng-state
                    elif 'energielabel' in label or 'epc label' in label:
                        data['epc_text'] = value
                    elif 'renovatieplicht' in label:
                        data['renovation_text'] = value
            
            # Extract location/address from h2 or main title
            location = data.get('location', '')
            if not location:
                # Try to get from page title or h2
                title_selectors = ['h2', 'h1', '.property-title', '.main-title']
                for selector in title_selectors:
                    title_elem = soup.select_one(selector)
                    if title_elem:
                        location = title_elem.get_text(strip=True)
                        break
            
            # Property type — derive from URL first (most reliable on Zimmo)
            property_type = "unknown"
            url_lower = property_url.lower()
            if '/appartement' in url_lower or '/apartment' in url_lower:
                property_type = "apartment"
            elif '/huis' in url_lower or '/woning' in url_lower or '/house' in url_lower:
                property_type = "house"
            elif '/studio' in url_lower:
                property_type = "studio"
            else:
                prop_type_text = data.get('property_type', '').lower()
                if 'appartement' in prop_type_text or 'apartment' in prop_type_text:
                    property_type = "apartment"
                elif 'huis' in prop_type_text or 'woning' in prop_type_text or 'house' in prop_type_text:
                    property_type = "house"
                elif 'studio' in prop_type_text:
                    property_type = "studio"

            # Process and normalize extracted data
            # Surface area
            surface_area = None
            surface_text = data.get('surface_area_text', '')
            if surface_text:
                surface_match = re.search(r'(\d+)', surface_text)
                if surface_match:
                    try:
                        surface_area = int(surface_match.group(1))
                    except ValueError:
                        pass

            # Bedrooms
            bedrooms = None
            bedrooms_text = data.get('bedrooms_text', '')
            if bedrooms_text:
                bedroom_match = re.search(r'(\d+)', bedrooms_text)
                if bedroom_match:
                    try:
                        bedrooms = int(bedroom_match.group(1))
                    except ValueError:
                        pass

            # Bathrooms
            bathrooms = None
            bathrooms_text = data.get('bathrooms_text', '')
            if bathrooms_text:
                bathroom_match = re.search(r'(\d+)', bathrooms_text)
                if bathroom_match:
                    try:
                        bathrooms = int(bathroom_match.group(1))
                    except ValueError:
                        pass
            
            # Extract postcode from location
            postcode = ""
            if location:
                postcode_match = re.search(r'\b([1-9]\d{3})\b', location)
                if postcode_match:
                    postcode = postcode_match.group(1)

            # Extract EPC score
            epc_score = ""
            epc_text = data.get('epc_text', '')
            if epc_text:
                letter_match = re.search(r'([A-G][+]{0,2})', epc_text, re.IGNORECASE)
                if letter_match:
                    epc_score = self._normalize_epc_label(letter_match.group(1))

            # Extract description before desc_fallback uses it
            description = ""
            desc_elem = soup.select_one('.section-description .description-block')
            if not desc_elem:
                for sel in [".property-description", "[class*='description']", ".description",
                            "[data-testid='description']", ".property-text"]:
                    desc_elem = soup.select_one(sel)
                    if desc_elem and len(desc_elem.get_text(strip=True)) > 50:
                        break
            if desc_elem:
                description = desc_elem.get_text(strip=True)

            # Description-text fallbacks when CSS selectors yielded nothing
            desc_fallback = (data.get('location', '') + ' ' + description) if not surface_area and not bedrooms and not epc_score else ''
            if desc_fallback:
                if not surface_area:
                    m = re.search(r'(\d{2,4})\s*m[²2]', desc_fallback, re.IGNORECASE)
                    if m:
                        try:
                            surface_area = int(m.group(1))
                        except ValueError:
                            pass
                if not bedrooms:
                    m = re.search(r'(\d+)\s*(?:slaapkamer|bedroom)', desc_fallback, re.IGNORECASE)
                    if m:
                        try:
                            bedrooms = int(m.group(1))
                        except ValueError:
                            pass
                if not epc_score:
                    m = re.search(r'energieklasse\s+([A-G][+]{0,2})', desc_fallback, re.IGNORECASE)
                    if m:
                        epc_score = self._normalize_epc_label(m.group(1))
            
            # Extract construction year
            construction_year = None
            const_year_text = data.get('construction_year_text', '')
            if const_year_text and 'op aanvraag' not in const_year_text.lower():
                year_match = re.search(r'(\d{4})', const_year_text)
                if year_match:
                    try:
                        construction_year = int(year_match.group(1))
                    except ValueError:
                        pass
            
            # Translate description to English
            translation_result = self.translator.translate_property_description(description)
            description_english = translation_result['translated']
            detected_lang = translation_result['detected_language']

            # Extract images
            image_url_1 = None
            image_url_2 = None
            img_tags = soup.select('img[src*="zimmo"]')
            property_images = [img['src'] for img in img_tags if 'property' in img.get('src', '').lower() or 'photo' in img.get('src', '').lower()]
            if len(property_images) > 0:
                image_url_1 = property_images[0]
            if len(property_images) > 1:
                image_url_2 = property_images[1]

            # Check for tenant situation
            has_tenant = self._check_tenant_situation(description)

            # Collect all property details for comprehensive extraction
            all_property_details = {
                'Surface': f"{surface_area}m²" if surface_area else None,
                'Bedrooms': bedrooms,
                'Bathrooms': bathrooms,
                'Construction year': construction_year,
                'EPC score': epc_score,
                'Property type': property_type,
                'HAS_TENANT': '⚠️ YES' if has_tenant else 'No',
                'Description Language': detected_lang.upper(),
                'Description (Original)': description,
                'Description (English)': description_english,
                'Image 1 URL': image_url_1,
                'Image 2 URL': image_url_2,
            }

            # Extract all other visible fields from raw_data
            for key, value in data.items():
                if key not in ['location', 'price_text', 'surface_area_text', 'bedrooms_text',
                               'bathrooms_text', 'construction_year_text', 'epc_text']:
                    field_name = key.replace('_text', '').replace('_', ' ').title()
                    all_property_details[field_name] = value

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
                'bathrooms': bathrooms,
                'construction_year': construction_year,
                'epc_score': epc_score,
                'description': description,
                'description_english': description_english,
                'description_language': detected_lang,
                'id': self._extract_id_from_url(property_url),
                'source': 'zimmo',
                'data_source': 'zimmo',
                'has_tenant': has_tenant,
                'under_option': False,  # Zimmo doesn't have this flag typically
                'image_url_1': image_url_1,
                'image_url_2': image_url_2,
                'all_property_details': all_property_details,
                # Additional raw data for debugging
                'raw_data': data
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
    
    def _check_tenant_situation(self, description: str) -> bool:
        """Check if property has current tenants."""
        tenant_keywords = [
            'tenant', 'rented', 'occupied', 'huurder', 'verhuurd', 'bezet',
            'rental income', 'current rent', 'lease', 'huurcontract',
            'locataire', 'loué', 'actuellement loué', 'currently rented'
        ]

        if description:
            desc_lower = description.lower()
            for keyword in tenant_keywords:
                if keyword in desc_lower:
                    return True
        return False

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
