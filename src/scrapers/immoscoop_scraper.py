"""
Immoscoop.be scraper - specialized scraper for Immoscoop real estate platform.
"""
from typing import List, Dict, Optional
from urllib.parse import urlencode
import time
import json
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from ..base_scraper import BasePropertyScraper
from ..translator import PropertyTranslator


class ImmoscoopScraper(BasePropertyScraper):
    """Scraper for Immoscoop.be - Belgian real estate platform."""
    
    def __init__(self):
        super().__init__("Immoscoop", "https://www.immoscoop.be")
        self.translator = PropertyTranslator()
    
    def _build_search_url(self, min_price: Optional[int] = None, max_price: Optional[int] = None, min_surface: Optional[int] = None,
                         epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None) -> str:
        params = {"offerType": "for-sale", "propertyTypes": "house,apartment"}
        if max_price:
            params['maxPrice'] = str(max_price)
        if min_price:
            params['minPrice'] = str(min_price)
        if min_surface:
            params['minLivableSurfaceArea'] = str(min_surface)
        if epc_scores:
            params['epcLabels'] = ','.join(str(s).strip() for s in epc_scores)
        if postal_codes:
            clean_codes = [c.replace('BE-', '').strip() for c in postal_codes if c.replace('BE-', '').strip().isdigit()]
            if clean_codes:
                params['postalCodes'] = ','.join(clean_codes)
        return "https://www.immoscoop.be/en/search/query?" + urlencode(params)

    
    def scrape_with_filters(self, min_price: Optional[int] = None, max_price: Optional[int] = None, min_surface: Optional[int] = None,
                          epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None, 
                          max_pages: int = 5, on_listing=None, on_checked=None,
                          should_cancel=None) -> List[Dict]:
        """Scrape Immoscoop with filters."""
        search_url = self._build_search_url(min_price, max_price, min_surface, epc_scores, postal_codes)
        print(f"🌐 Scraping Immoscoop with URL: {search_url}")
        
        return self.scrape_from_url(search_url, max_pages, on_listing, on_checked, should_cancel)


    def scrape_from_url(self, search_url: str, max_pages: int = 5, on_listing=None,
                        on_checked=None, should_cancel=None) -> List[Dict]:
        """Scrape Immoscoop from a specific search URL."""
        properties = []
        driver = None
        
        try:
            # Set up Chrome driver - Immoscoop needs JavaScript
            driver = self._setup_chrome_driver()
            # Re-enable JavaScript for React/Next.js site
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"🚀 Starting Immoscoop scraping (max {max_pages} pages, will stop if no more results)...")
            
            page = 1
            no_results_count = 0  # Track consecutive pages with no results
            
            while page <= max_pages:
                print(f"\n📄 Scraping Immoscoop page {page}/{max_pages}...")
                
                # Build page URL - Immoscoop uses different pagination
                if page == 1:
                    page_url = search_url
                else:
                    separator = '&' if '?' in search_url else '?'
                    page_url = f"{search_url}{separator}page={page}"
                
                print(f"   URL: {page_url}")
                driver.get(page_url)
                
                # Wait for React content to load
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-selector='property-card:card:vertical']"))
                    )
                    time.sleep(2)
                except TimeoutException:
                    print(f"⏱️  Timeout waiting for property cards on page {page}")
                    pass
                
                # Extract property URLs from this page using multiple selectors
                property_links = self._extract_property_links(driver)
                
                if not property_links:
                    no_results_count += 1
                    print(f"   No properties found on page {page} - checking for end of results")
                    
                    # Check for end-of-results indicators in the page
                    page_source = driver.page_source.lower()
                    end_indicators = [
                        "geen resultaten", "no results", "geen woningen gevonden", 
                        "no properties found", "einde resultaten", "end of results",
                        "geen panden gevonden", "no listings found"
                    ]
                    
                    if any(indicator in page_source for indicator in end_indicators):
                        print(f"   ✅ Reached end of results on page {page}")
                        break
                    
                    # If we have 2 consecutive pages with no results, likely at the end
                    if no_results_count >= 2:
                        print(f"   ✅ No results for {no_results_count} consecutive pages - stopping")
                        break
                    
                    # Try next page
                    page += 1
                    continue
                else:
                    no_results_count = 0  # Reset counter when we find results
                
                print(f"   Found {len(property_links)} property URLs on page {page}")
                
                # Scrape individual properties
                for i, property_url in enumerate(property_links, 1):
                    if should_cancel and should_cancel():
                        break
                    # Make URL absolute if needed
                    if property_url.startswith('/'):
                        property_url = f"https://www.immoscoop.be{property_url}"

                    if not self._postcode_allowed(property_url):
                        print(f"   ⏭️  [{i}/{len(property_links)}] Skipping postcode mismatch: {property_url}")
                        if on_checked:
                            on_checked()
                        continue
                    
                    if self.is_property_already_scraped(property_url):
                        print(f"[{i}/{len(property_links)}] Skipping already scraped property:{property_url} ")
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
                    time.sleep(4)  # Be respectful with requests - React sites can be sensitive
                if should_cancel and should_cancel():
                    break
                time.sleep(6)  # Longer delay between pages for React site
                page += 1  # Move to next page
        
        finally:
            if driver:
                driver.quit()
        
        # Print summary
        successfully_scraped = len(properties)
        print(f"\n🎉 Immoscoop Scraping Summary:")
        print(f"   ✅ Successfully scraped: {successfully_scraped}")
        if successfully_scraped > 0:
            print(f"   🏠 Average price: €{sum(p.get('price', 0) for p in properties) / len(properties):,.0f}")
        
        # Auto-export to JSON
        if properties:
            self.export_to_json()
        
        return properties
    
    def _extract_property_links(self, driver) -> List[str]:
        elements = driver.find_elements(By.CSS_SELECTOR, "[data-selector='property-card:card:vertical']")
        seen = set()
        unique_links = []
        for el in elements:
            href = el.get_attribute("href") or ""
            if href and href not in seen:
                seen.add(href)
                unique_links.append(href)
        return unique_links
    
    def _scrape_property_details(self, property_url: str, driver=None) -> Optional[Dict]:
        """Scrape detailed information for a single Immoscoop property."""
        if not driver:
            print("   Warning: No driver provided to _scrape_property_details")
            return None
        
        try:
            print(f"   🔍 Accessing Immoscoop property: {property_url}")
            driver.get(property_url)
            
            # Wait for Next.js content to load
            try:
                WebDriverWait(driver, 20).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='property-price']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".property-price")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='PropertyPrice']")),
                        EC.presence_of_element_located((By.TAG_NAME, "h1"))  # Fallback
                    )
                )
                time.sleep(3)  # Additional wait for React to fully render
            except TimeoutException:
                print("   ⚠ Timeout waiting for property content")
            
            try:
                # First priority: Try to get Next.js data from JavaScript context
                print("   📊 Attempting to extract Next.js JSON data...")
                next_data = None
                try:
                    # Try to get __NEXT_DATA__ from JavaScript
                    next_data = driver.execute_script("return window.__NEXT_DATA__ || null;")
                    if next_data and 'props' in next_data and 'pageProps' in next_data['props']:
                        print("   ✅ Found Next.js data - using rich property information")
                        property_data = self._extract_from_next_data(next_data, property_url)
                        if property_data:
                            return property_data
                except Exception as e:
                    print(f"   ⚠ Could not extract Next.js data: {e}")
                
                # Fallback: Parse HTML if JavaScript data not available
                print("   ⚠ Next.js data not available, using HTML parsing fallback")
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Try to extract __NEXT_DATA__ from script tag
                script_tags = soup.find_all('script', {'id': '__NEXT_DATA__'})
                for script in script_tags:
                    if script.string:
                        try:
                            next_data = json.loads(script.string)
                            if 'props' in next_data and 'pageProps' in next_data['props']:
                                print("   ✅ Found Next.js data in HTML - using rich property information")
                                property_data = self._extract_from_next_data(next_data, property_url)
                                if property_data:
                                    return property_data
                        except json.JSONDecodeError:
                            continue
                
                # Final fallback: Extract basic property information from HTML
                print("   ⚠ Using basic HTML parsing as final fallback")
                property_data = self._extract_immoscoop_data(soup, property_url)
                
                if not property_data:
                    print("   ❌ Could not extract property data")
                    return None
                
                return property_data
                
            except Exception as e:
                print(f"   Error parsing property data: {e}")
                return None
                
        except Exception as e:
            print(f"   Error scraping Immoscoop property: {e}")
            return None
    
    def _extract_immoscoop_data(self, soup: BeautifulSoup, property_url: str) -> Optional[Dict]:
        """Extract property data from Immoscoop HTML using BeautifulSoup."""
        try:
            # Extract price
            price = 0
            price_selectors = [
                "[data-testid='property-price']",
                ".property-price",
                "[class*='PropertyPrice']",
                "[class*='price']"
            ]
            
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = self._extract_price_from_text(price_text)
                    if price > 0:
                        break
            
            # Extract location/address
            location = ""
            location_selectors = [
                "[data-testid='property-address']",
                ".property-address", 
                "[class*='PropertyAddress']",
                "[class*='address']",
                "h1"  # Sometimes location is in the main heading
            ]
            
            for selector in location_selectors:
                location_elem = soup.select_one(selector)
                if location_elem:
                    location = location_elem.get_text(strip=True)
                    if location and len(location) > 5:  # Basic validation
                        break
            
            # Extract surface area
            surface_area = None
            surface_keywords = ["oppervlakte", "surface", "m²", "m2"]
            
            # Look for surface area in various elements
            all_text_elements = soup.find_all(text=True)
            for text in all_text_elements:
                text_lower = str(text).lower()
                if any(keyword in text_lower for keyword in surface_keywords):
                    # Try to extract number before or after m²
                    surface_match = re.search(r'(\d+)\s*m[²2]', text_lower)
                    if surface_match:
                        surface_area = int(surface_match.group(1))
                        break
            
            # Extract bedrooms
            bedrooms = None
            bedroom_keywords = ["slaapkamer", "bedroom", "kamer"]
            
            for text in all_text_elements:
                text_lower = str(text).lower()
                if any(keyword in text_lower for keyword in bedroom_keywords):
                    # Look for number + bedroom word
                    bedroom_match = re.search(r'(\d+)\s*(?:slaapkamer|bedroom|kamer)', text_lower)
                    if bedroom_match:
                        bedrooms = int(bedroom_match.group(1))
                        break
            
            # EPC label/score extraction (unified approach like Zimmo)
            epc_score = ""
            all_text = soup.get_text()
            epc_patterns = [
                r'EPC[:\s]*([A-G][+]*)',
                r'energie[:\s]*([A-G][+]*)',
                r'energy[:\s]*([A-G][+]*)',
                r'epc\s+label[:\s]*([A-G][+]*)',
                r'([A-G][+]{0,2})\s*(?:energy|EPC)',
            ]
            
            for pattern in epc_patterns:
                epc_match = re.search(pattern, all_text, re.IGNORECASE)
                if epc_match:
                    epc_score = epc_match.group(1).upper()
                    break


            # Extract property type
            property_type = "unknown"
            type_keywords = {
                "appartement": "apartment",
                "apartment": "apartment", 
                "huis": "house",
                "house": "house",
                "villa": "house",
                "studio": "studio"
            }
            
            page_text = soup.get_text().lower()
            for keyword, normalized_type in type_keywords.items():
                if keyword in page_text:
                    property_type = normalized_type
                    break
            
            # Extract postcode from location
            postcode = ""
            if location:
                postcode_match = re.search(r'\b([1-9]\d{3})\b', location)
                if postcode_match:
                    postcode = postcode_match.group(1)
            
            # Extract description
            description = ""
            description_selectors = [
                "[data-testid='property-description']",
                ".property-description",
                "[class*='PropertyDescription']",
                "[class*='description']"
            ]

            for selector in description_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    if len(description) > 50:  # Basic validation
                        break

            # Translate description
            translation_result = self.translator.prepare_description(description)
            description_english = translation_result['translated']
            detected_lang = translation_result['detected_language']

            # Extract all images
            img_tags = soup.select('img[src]')
            property_images = [img.get('src', '') for img in img_tags
                               if img.get('src', '') and
                               ('property' in img.get('src', '').lower() or
                                'photo' in img.get('src', '').lower() or
                                'image' in img.get('src', '').lower() or
                                'immoscoop' in img.get('src', '').lower())]

            # Make URLs absolute
            property_images = [img if img.startswith('http') else f"https://www.immoscoop.be{img}"
                              for img in property_images]

            image_url_1 = property_images[0] if len(property_images) > 0 else None
            image_url_2 = property_images[1] if len(property_images) > 1 else None

            # Check for tenant situation
            has_tenant = self._check_tenant_situation(description)

            # Extract bathrooms
            bathrooms = None
            bathroom_keywords = ["badkamer", "bathroom", "salle de bain"]
            for text in all_text_elements:
                text_lower = str(text).lower()
                if any(keyword in text_lower for keyword in bathroom_keywords):
                    bathroom_match = re.search(r'(\d+)\s*(?:badkamer|bathroom|salle)', text_lower)
                    if bathroom_match:
                        bathrooms = int(bathroom_match.group(1))
                        break

            # Build comprehensive property details
            all_property_details = {
                'Surface': f"{surface_area}m²" if surface_area else None,
                'Bedrooms': bedrooms,
                'Bathrooms': bathrooms,
                'EPC Score': epc_score,
                'Property Type': property_type.title(),
                'HAS_TENANT': '⚠️ YES' if has_tenant else 'No',
                'Description Language': detected_lang.upper(),
                'Description (Original)': description,
                'Description (English)': description_english,
                'Image 1 URL': image_url_1,
                'Image 2 URL': image_url_2,
            }

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
                'epc_score': epc_score,
                'description': description,
                'description_english': description_english,
                'description_language': detected_lang,
                'has_tenant': has_tenant,
                'image_url_1': image_url_1,
                'image_url_2': image_url_2,
                'images': property_images,
                'all_property_details': all_property_details,
                'id': self._extract_id_from_url(property_url),
                'source': 'immoscoop'
            }
            
            # Only return if we have at least price and location
            if price > 0 and location:
                return property_data
            else:
                print(f"   ⚠ Insufficient data: price={price}, location='{location}'")
                return None
                
        except Exception as e:
            print(f"   Error extracting Immoscoop data: {e}")
            return None
    
    def _extract_price_from_text(self, price_text: str) -> float:
        """Extract numeric price from text."""
        if not price_text:
            return 0
        
        # Remove currency symbols and spaces
        clean_text = price_text.replace('€', '').replace(',', '').replace('.', '').replace(' ', '')
        
        # Look for numbers
        price_match = re.search(r'(\d+)', clean_text)
        if price_match:
            try:
                return float(price_match.group(1))
            except ValueError:
                pass
        
        return 0
    
    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract property ID from Immoscoop URL."""
        # Immoscoop URLs typically have IDs in them
        id_match = re.search(r'/pand/(\d+)', url) or re.search(r'/property/(\d+)', url)
        if id_match:
            return id_match.group(1)

        # Fallback - use last part of URL
        return url.split('/')[-1] if url else None

    def _check_tenant_situation(self, description: str) -> bool:
        """Check if property has current tenant based on description."""
        if not description:
            return False

        tenant_keywords = [
            'tenant', 'rented', 'occupied', 'huurder', 'verhuurd', 'bezet',
            'rental income', 'current rent', 'lease', 'huurcontract',
            'locataire', 'loué', 'actuellement loué', 'currently rented',
            'huurinkomsten', 'huurprijs', 'maandelijkse huur'
        ]

        desc_lower = description.lower()
        for keyword in tenant_keywords:
            if keyword in desc_lower:
                return True

        return False
    
    def _extract_from_next_data(self, next_data: dict, property_url: str) -> Optional[Dict]:
        """Extract comprehensive property data from Next.js __NEXT_DATA__ object based on actual Immoscoop structure."""
        try:
            # Navigate to the property data within Next.js structure
            page_props = next_data.get('props', {}).get('pageProps', {})
            property_data = page_props.get('property', {})
            
            if not property_data:
                print("   ⚠ No property data found in Next.js object")
                return None
            
            # Extract basic information
            property_id = property_data.get('id', '') or property_data.get('canonicalId', '')
            title = property_data.get('title', '') or property_data.get('h1Title', '')
            meta_title = property_data.get('metaTitle', '')
            
            # Extract price information
            price = 0
            price_info = property_data.get('price', {})
            if isinstance(price_info, dict):
                price_label = price_info.get('label', '')
                # Extract numeric value from label like "€249,000"
                if price_label:
                    price_match = re.search(r'€?([\d,]+)', price_label.replace('.', ','))
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))
            
            # Extract address information
            address_data = property_data.get('address', {})
            geo_data = address_data.get('geo', {})
            city_data = address_data.get('city', {})
            municipality_data = address_data.get('municipality', {})
            house_number_data = address_data.get('houseNumber', {})
            
            street = address_data.get('street', '')
            house_number = house_number_data.get('number', '') if isinstance(house_number_data, dict) else str(house_number_data)
            full_address = f"{street} {house_number}".strip()
            
            city = city_data.get('label', '') if isinstance(city_data, dict) else str(city_data)
            municipality = municipality_data.get('label', '') if isinstance(municipality_data, dict) else str(municipality_data)
            postal_code = address_data.get('postalCode', '')
            
            # Extract coordinates
            latitude = geo_data.get('lat', None)
            longitude = geo_data.get('long', None)
            
            # Extract features from the features array
            features_list = property_data.get('features', [])
            surface_area = None
            bedrooms = None
            bathrooms = None
            epc_score = ""
            terrain_area = None
            
            for feature in features_list:
                if isinstance(feature, dict):
                    feature_id = feature.get('id', '')
                    feature_value = feature.get('value', '')
                    
                    if feature_id == 'livableSurfaceArea' and feature_value:
                        try:
                            surface_area = int(feature_value)
                        except ValueError:
                            pass
                    elif feature_id == 'BedroomNumber' and feature_value:
                        try:
                            bedrooms = int(feature_value)
                        except ValueError:
                            pass
                    elif feature_id == 'BathroomNumber' and feature_value:
                        try:
                            bathrooms = int(feature_value)
                        except ValueError:
                            pass
                    elif feature_id == 'EpcClass' and feature_value:
                        epc_score = self._normalize_epc_label(feature_value)
                    elif feature_id == 'TerrainArea' and feature_value:
                        try:
                            terrain_area = int(feature_value)
                        except ValueError:
                            pass
            
            # Extract property type
            property_type_data = property_data.get('propertyType', {})
            property_type = property_type_data.get('label', '').lower() if isinstance(property_type_data, dict) else 'unknown'
            if 'house' in property_type:
                property_type = 'house'
            elif 'apartment' in property_type:
                property_type = 'apartment'
            elif not property_type:
                # Try to infer from title
                title_lower = title.lower()
                if 'apartment' in title_lower or 'flat' in title_lower:
                    property_type = 'apartment'
                elif 'house' in title_lower:
                    property_type = 'house'
                else:
                    property_type = 'unknown'
            
            # Extract description
            description = property_data.get('description', '')

            # Translate description
            translation_result = self.translator.prepare_description(description)
            description_english = translation_result['translated']
            detected_lang = translation_result['detected_language']

            # Extract agent information
            agent_data = property_data.get('agent', {})
            agent_name = agent_data.get('name', '')
            agent_phone = agent_data.get('phone', '')
            agent_email = agent_data.get('email', '')

            # Extract images and first 2 image URLs
            images = property_data.get('images', [])
            image_count = len(images) if isinstance(images, list) else 0
            image_url_1 = images[0] if len(images) > 0 else None
            image_url_2 = images[1] if len(images) > 1 else None

            # Check for tenant situation
            has_tenant = self._check_tenant_situation(description)
            
            # Extract comprehensive property details from propertyDetailGroups
            construction_year = None
            renovation_year = None
            property_detail_groups = property_data.get('propertyDetailGroups', [])
            
            # Initialize comprehensive property details storage
            detailed_property_info = {
                'financial': {},
                'building': {},
                'terrain': {},
                'location': {},
                'layout': {},
                'comfort': {},
                'energy': {},
                'urban_planning': {},
                'all_details': {}  # Store all details for backward compatibility
            }
            
            # Extract all property details from each group
            for group in property_detail_groups:
                if isinstance(group, dict):
                    group_name = group.get('group', '').lower()
                    property_details = group.get('propertyDetails', [])
                    
                    for detail in property_details:
                        if isinstance(detail, dict):
                            title_detail = detail.get('title', '')
                            description_detail = detail.get('description', '')
                            
                            # Store in appropriate category
                            category_key = group_name.lower().replace(' ', '_')
                            if category_key in detailed_property_info:
                                detailed_property_info[category_key][title_detail] = description_detail
                            
                            # Store in all_details for easy access
                            detailed_property_info['all_details'][title_detail] = description_detail
                            
                            # Extract specific commonly needed fields for backward compatibility
                            if 'Construction year' in title_detail and description_detail.isdigit():
                                construction_year = int(description_detail)
                            elif 'Renovation year' in title_detail and description_detail.isdigit():
                                renovation_year = int(description_detail)
                            elif 'Surface' in title_detail and not surface_area:
                                # Extract surface area if not already found in features
                                surface_match = re.search(r'(\d+)', description_detail)
                                if surface_match:
                                    try:
                                        surface_area = int(surface_match.group(1))
                                    except ValueError:
                                        pass
                            elif 'Number of bedrooms' in title_detail and not bedrooms:
                                # Extract bedrooms if not already found in features
                                try:
                                    bedrooms = int(description_detail)
                                except ValueError:
                                    pass
                            elif 'Number of bathrooms' in title_detail and not bathrooms:
                                # Extract bathrooms if not already found in features
                                try:
                                    bathrooms = int(description_detail)
                                except ValueError:
                                    pass
                            elif 'EPC label' in title_detail and not epc_score:
                                epc_score = self._normalize_epc_label(description_detail)
                            elif 'EPC score' in title_detail and not epc_score:
                                pass
                            elif 'Plot size' in title_detail and not terrain_area:
                                # Extract terrain area from plot size
                                terrain_match = re.search(r'(\d+)', description_detail)
                                if terrain_match:
                                    try:
                                        terrain_area = int(terrain_match.group(1))
                                    except ValueError:
                                        pass
            
            # Build comprehensive all_property_details for Excel export
            all_property_details = {
                'Surface': f"{surface_area}m²" if surface_area else None,
                'Bedrooms': bedrooms,
                'Bathrooms': bathrooms,
                'EPC Score': epc_score,
                'Property Type': property_type.title(),
                'Construction Year': construction_year,
                'Renovation Year': renovation_year,
                'Terrain Area': f"{terrain_area}m²" if terrain_area else None,
                'HAS_TENANT': '⚠️ YES' if has_tenant else 'No',
                'Description Language': detected_lang.upper(),
                'Description (Original)': description,
                'Description (English)': description_english,
                'Image 1 URL': image_url_1,
                'Image 2 URL': image_url_2,
                'Agent Name': agent_name,
                'Agent Phone': agent_phone,
                'Agent Email': agent_email,
            }

            # Add all extracted details to all_property_details
            all_property_details.update(detailed_property_info['all_details'])

            # Build comprehensive property data
            enriched_data = {
                # Core information
                'url': property_url,
                'id': property_id,
                'name': title or meta_title,
                'title': title,
                'meta_title': meta_title,
                'price': price,
                'location': f"{city}, {postal_code}, {full_address}".strip().strip(','),
                'postcode': str(postal_code) if postal_code else "",
                'property_type': property_type,

                # Property details
                'surface_area': surface_area,
                'bedrooms': bedrooms,
                'bathrooms': bathrooms,
                'construction_year': construction_year,
                'renovation_year': renovation_year,
                'epc_score': epc_score,
                'description': description,
                'description_english': description_english,
                'description_language': detected_lang,
                'terrain_area': terrain_area,
                'has_tenant': has_tenant,
                'image_url_1': image_url_1,
                'image_url_2': image_url_2,
                'images': images,

                # Location details
                'address': full_address,
                'street': street,
                'house_number': house_number,
                'city': city,
                'municipality': municipality,
                'latitude': latitude,
                'longitude': longitude,

                # Agent information
                'agent_name': agent_name,
                'agent_phone': agent_phone,
                'agent_email': agent_email,

                # Media
                'image_count': image_count,

                # Source identifier
                'source': 'immoscoop',
                'data_source': 'nextjs_json',

                # Comprehensive property details from propertyDetailGroups
                'property_details': detailed_property_info,

                # Individual category access for easier processing
                'financial_details': detailed_property_info['financial'],
                'building_details': detailed_property_info['building'],
                'terrain_details': detailed_property_info['terrain'],
                'location_details': detailed_property_info['location'],
                'layout_details': detailed_property_info['layout'],
                'comfort_details': detailed_property_info['comfort'],
                'energy_details': detailed_property_info['energy'],
                'urban_planning_details': detailed_property_info['urban_planning'],

                # All details in flat structure for backward compatibility and easy searching
                'all_property_details': all_property_details,
            }
            
            # Only return if we have minimum required data
            if price > 0 and title:
                print(f"   ✅ Extracted rich property data: {title} - €{price:,.0f}")
                return enriched_data
            else:
                print(f"   ⚠ Insufficient Next.js data: price={price}, title='{title}'")
                return None
                
        except Exception as e:
            print(f"   ❌ Error extracting from Next.js data: {e}")
            return None
    
    def _extract_property_urls(self, page_source: str, base_url) -> List[str]:
        """Extract property URLs from Immoscoop search results page."""
        # This method is used by the base class but we handle URL extraction in scrape_from_url
        return []
