"""Immovlan.be scraper."""
import json
import re
import time
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from ..base_scraper import BasePropertyScraper


class ImmovlanScraper(BasePropertyScraper):
    """Scrape Belgian listings from Immovlan's server-rendered pages."""

    def __init__(self):
        super().__init__("Immovlan", "https://immovlan.be")

    def _build_search_url(self, min_price=None, max_price=None, min_surface=None,
                          epc_scores=None, postal_codes=None):
        params = {
            "transactiontypes": "for-sale",
            "propertytypes": "house,apartment",
        }
        if min_price:
            params["minprice"] = str(min_price)
        if max_price:
            params["maxprice"] = str(max_price)
        if min_surface:
            params["minlivablesurface"] = str(min_surface)
        if epc_scores:
            scores = [str(score).replace("BE-", "").strip() for score in epc_scores]
            scores = [score for score in scores if score in {"A++", "A+", "A", "B", "C", "D", "E", "F", "G"}]
            if scores:
                params["energyclasses"] = ",".join(scores)
        if postal_codes:
            codes = [str(code).replace("BE-", "").strip() for code in postal_codes]
            codes = [code for code in codes if re.fullmatch(r"\d{4}", code)]
            if codes:
                params["postalcode"] = ",".join(codes)
        return self.base_url + "/en/real-estate?" + urlencode(params)

    def scrape_with_filters(self, min_price=None, max_price=None, min_surface=None,
                            epc_scores=None, postal_codes=None, max_pages=5,
                            on_listing=None, on_checked=None, should_cancel=None):
        search_url = self._build_search_url(min_price, max_price, min_surface, epc_scores, postal_codes)
        print(f"[Immovlan] search url: {search_url}")
        return self.scrape_from_url(
            search_url,
            max_pages, on_listing, on_checked, should_cancel,
        )

    def scrape_from_url(self, search_url, max_pages=5, on_listing=None,
                        on_checked=None, should_cancel=None):
        properties = []
        driver = None
        try:
            driver = self._setup_chrome_driver()
            for page in range(1, max_pages + 1):
                if should_cancel and should_cancel():
                    break
                page_url = search_url
                if page > 1:
                    separator = "&" if "?" in search_url else "?"
                    page_url += separator + "page=" + str(page)
                print(f"[Immovlan] fetch search page {page}: {page_url}")
                driver.get(page_url)
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a.v3-property-card"))
                    )
                except TimeoutException:
                    pass
                links = self._extract_property_urls(driver.page_source, self.base_url)
                print(f"[Immovlan] discovered {len(links)} listing links on page {page}")
                if not links:
                    break
                for property_url in links:
                    if should_cancel and should_cancel():
                        break
                    if not self._postcode_allowed(property_url):
                        print(f"[Immovlan] skip postcode mismatch: {property_url}")
                        if on_checked:
                            on_checked()
                        continue
                    if self.is_property_already_scraped(property_url):
                        print(f"[Immovlan] skip already fetched: {property_url}")
                        if on_checked:
                            on_checked()
                        continue
                    data = self._scrape_property_details(property_url, driver)
                    print(f"[Immovlan] {'parsed' if data else 'no data'}: {property_url}")
                    if data:
                        normalized = self._normalize_property_data(data)
                        self.properties.append(normalized)
                        properties.append(normalized)
                        self.existing_properties.add(property_url)
                        if on_listing:
                            on_listing(normalized)
                    if on_checked:
                        on_checked()
                    time.sleep(2)
                time.sleep(2)
        finally:
            if driver:
                driver.quit()
        if properties:
            self.export_to_json()
        print(f"[Immovlan] completed: {len(properties)} listings")
        return properties

    def _scrape_property_details(self, property_url, driver=None):
        if not driver:
            return None
        try:
            print(f"[Immovlan] fetch detail: {property_url}")
            driver.get(property_url)
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "script[type='application/ld+json']"))
                )
            except TimeoutException:
                pass
            return self._extract_immovlan_data(
                BeautifulSoup(driver.page_source, "html.parser"), property_url
            )
        except Exception as exc:
            print(f"Error scraping Immovlan property: {exc}")
            return None

    def _extract_property_urls(self, page_source, base_url=None):
        base_url = base_url or self.base_url
        soup = BeautifulSoup(page_source, "html.parser")
        urls = []
        seen = set()
        for anchor in soup.select("a.v3-property-card, a[href*='/detail/']"):
            href = anchor.get("href", "")
            if "/detail/" not in href:
                continue
            absolute = urljoin(base_url, href)
            parts = urlsplit(absolute)
            normalized = urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))
            if normalized not in seen:
                seen.add(normalized)
                urls.append(normalized)
        return urls

    def _extract_property_links(self, driver):
        return self._extract_property_urls(driver.page_source, self.base_url)

    def _extract_immovlan_data(self, soup, property_url):
        listing = None
        for script in soup.select("script[type='application/ld+json']"):
            try:
                value = json.loads(script.string or script.get_text())
            except (TypeError, json.JSONDecodeError):
                continue
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                if isinstance(candidate, dict) and candidate.get("@type") == "RealEstateListing":
                    listing = candidate
                    break
            if listing:
                break
        if not listing:
            return None

        entity = listing.get("mainEntity") or {}
        address = entity.get("address") or {}
        offer = listing.get("offers") or {}
        if isinstance(offer, list):
            offer = offer[0] if offer else {}
        price = self._safe_float(offer.get("price")) or 0
        location = ", ".join(part for part in [
            address.get("streetAddress", ""),
            " ".join(part for part in [address.get("postalCode", ""), address.get("addressLocality", "")] if part),
        ] if part)
        property_type = self._property_type(entity.get("@type", ""), property_url)
        images = listing.get("image") or []
        if isinstance(images, str):
            images = [images]
        identifier = self._extract_id_from_url(property_url)
        geo = entity.get("geo") or {}
        floor_size = entity.get("floorSize") or {}
        features = " ".join(str(value) for value in [
            listing.get("description", ""), listing.get("keywords", ""),
            entity.get("description", ""), entity.get("keywords", ""),
            entity.get("amenityFeature", ""), entity.get("additionalProperty", ""),
        ]).lower()
        terrace = bool(re.search(r"\bterrace\b|\bterras\b|\bterrasse\b", features))
        garden = bool(re.search(r"\bgarden\b|\btuin\b|\bjardin\b", features))
        return {
            "id": identifier,
            "url": property_url,
            "name": listing.get("name") or location,
            "price": price,
            "location": location,
            "postcode": address.get("postalCode", ""),
            "property_type": property_type,
            "surface_area": self._safe_float(floor_size.get("value")),
            "bedrooms": self._safe_int(entity.get("numberOfBedrooms")),
            "bathrooms": self._safe_int(entity.get("numberOfBathroomsTotal")),
            "construction_year": self._safe_int(entity.get("yearBuilt")),
            "latitude": self._safe_float(geo.get("latitude")),
            "longitude": self._safe_float(geo.get("longitude")),
            "description": listing.get("description", ""),
            "image_url_1": images[0] if images else None,
            "image_url_2": images[1] if len(images) > 1 else None,
            "images": images,
            "outdoor_terrace": terrace,
            "outdoor_garden": garden,
            "source": "immovlan",
            "data_source": "immovlan_json_ld",
        }

    def _property_type(self, value, property_url):
        text = (str(value) + " " + property_url).lower()
        if "apartment" in text or "flat" in text:
            return "apartment"
        if any(item in text for item in ["house", "residence", "villa", "bungalow"]):
            return "house"
        if "studio" in text:
            return "studio"
        return ""

    def _extract_id_from_url(self, property_url):
        match = re.search(r"/([a-z0-9]{5,})/?$", property_url, re.IGNORECASE)
        return match.group(1).upper() if match else property_url.rstrip("/").rsplit("/", 1)[-1]
