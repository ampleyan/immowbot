"""Realo.be scraper using the site's listing links and structured metadata."""

import json
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from ..base_scraper import BasePropertyScraper


class RealoScraper(BasePropertyScraper):
    """Scraper for sale listings on Realo.be."""

    def __init__(self):
        super().__init__("Realo", "https://www.realo.be")

    def _build_search_url(
        self,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_surface: Optional[int] = None,
        epc_scores: Optional[List[str]] = None,
        postal_codes: Optional[List[str]] = None,
    ) -> str:
        params = {"offerType": "for-sale", "propertyTypes": "house,apartment"}
        if min_price:
            params["priceMin"] = str(min_price)
        if max_price:
            params["priceMax"] = str(max_price)
        if min_surface:
            params["surfaceMin"] = str(min_surface)
        if epc_scores:
            scores = [str(score).replace("BE-", "").strip().upper() for score in epc_scores]
            scores = [score for score in scores if score in {"A++", "A+", "A", "B", "C", "D", "E", "F", "G"}]
            if scores:
                params["energyClasses"] = ",".join(scores)
        if postal_codes:
            codes = [str(code).replace("BE-", "").strip() for code in postal_codes]
            codes = [code for code in codes if code.isdigit() and len(code) == 4]
            if codes:
                params["postalCodes"] = ",".join(codes)
        codes = [str(code).replace("BE-", "").strip() for code in (postal_codes or [])]
        location = next((f"antwerpen-{code}" for code in codes if code in {"2000", "2018", "2020", "2060"}), "antwerpen-2000")
        return f"{self.base_url}/nl/search/{location}?{urlencode(params)}"

    def scrape_with_filters(
        self,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_surface: Optional[int] = None,
        epc_scores: Optional[List[str]] = None,
        postal_codes: Optional[List[str]] = None,
        max_pages: int = 5,
        on_listing=None,
        on_checked=None,
        should_cancel=None,
    ) -> List[Dict]:
        search_url = self._build_search_url(min_price, max_price, min_surface, epc_scores, postal_codes)
        print(f"[Realo] search url: {search_url}")
        return self.scrape_from_url(search_url, max_pages, on_listing, on_checked, should_cancel)

    def scrape_from_url(
        self,
        search_url: str,
        max_pages: int = 5,
        on_listing=None,
        on_checked=None,
        should_cancel=None,
    ) -> List[Dict]:
        properties = []
        driver = None
        try:
            driver = self._setup_chrome_driver()
            for page in range(1, max_pages + 1):
                if should_cancel and should_cancel():
                    break
                page_url = search_url if page == 1 else f"{search_url}&page={page}"
                print(f"[Realo] fetch search page {page}: {page_url}")
                driver.get(page_url)
                links = self._extract_property_urls(driver.page_source, self.base_url)
                print(f"[Realo] discovered {len(links)} listing links on page {page}")
                if not links:
                    break
                for property_url in links:
                    if should_cancel and should_cancel():
                        break
                    if self.is_property_already_scraped(property_url):
                        print(f"[Realo] skip already fetched: {property_url}")
                        if on_checked:
                            on_checked()
                        continue
                    raw = self._scrape_property_details(property_url, driver)
                    print(f"[Realo] {'parsed' if raw else 'no data'}: {property_url}")
                    if raw:
                        property_data = self._normalize_property_data(raw)
                        self.properties.append(property_data)
                        properties.append(property_data)
                        self.existing_properties.add(property_url)
                        if on_listing:
                            on_listing(property_data)
                    if on_checked:
                        on_checked()
                    time.sleep(2)
                time.sleep(3)
        finally:
            if driver:
                driver.quit()
        if properties:
            self.export_to_json()
        print(f"[Realo] completed: {len(properties)} listings")
        return properties

    def _extract_property_urls(self, page_source: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(page_source, "html.parser")
        urls = []
        seen = set()
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "").strip()
            absolute = urljoin(base_url, href)
            parts = urlsplit(absolute)
            if parts.netloc not in {"www.realo.be", "realo.be"}:
                continue
            path = parts.path.rstrip("/")
            if not re.search(r"/(?:nl|fr|en)/(?:appartement|huis|woning|studio|villa)/[^/]+/\d+$", path, re.I) and not re.search(r"/(?:nl|fr|en)/[^/]+/\d{5,}$", path, re.I):
                continue
            clean_url = urlunsplit((parts.scheme, parts.netloc, path, "", ""))
            if clean_url not in seen:
                seen.add(clean_url)
                urls.append(clean_url)
        return urls

    def _scrape_property_details(self, property_url: str, driver=None) -> Optional[Dict]:
        if not driver:
            return None
        try:
            print(f"[Realo] fetch detail: {property_url}")
            driver.get(property_url)
            return self._parse_property_html(driver.page_source, property_url)
        except Exception as exc:
            print(f"Error scraping Realo property {property_url}: {exc}")
            return None

    def _parse_property_html(self, page_source: str, property_url: str) -> Dict:
        soup = BeautifulSoup(page_source, "html.parser")
        data = self._find_json_ld(soup)
        if not data:
            data = self._find_next_data(soup)
        address = data.get("address") if isinstance(data.get("address"), dict) else {}
        offer = data.get("offers") if isinstance(data.get("offers"), dict) else {}
        floor_size = data.get("floorSize") if isinstance(data.get("floorSize"), dict) else {}
        images = data.get("image", [])
        if isinstance(images, str):
            images = [images]
        meta = lambda name: self._meta_content(soup, name)
        price = self._number(offer.get("price") or data.get("price") or meta("price"))
        location = address.get("addressLocality") or meta("addressLocality") or meta("location")
        postcode = address.get("postalCode") or meta("postalCode")
        name = data.get("name") or meta("og:title") or (soup.title.get_text(" ", strip=True) if soup.title else "")
        description = data.get("description") or meta("description")
        rooms = data.get("numberOfRooms") or data.get("numberOfBedrooms") or meta("numberOfRooms")
        surface = floor_size.get("value") or data.get("surface_area") or meta("floorSize")
        geo = data.get("geo") if isinstance(data.get("geo"), dict) else {}
        features = " ".join(str(data.get(key, "")) for key in ("description", "keywords", "amenityFeature", "additionalProperty")).lower()
        terrace = bool(re.search(r"\bterrace\b|\bterras\b|\bterrasse\b", features))
        garden = bool(re.search(r"\bgarden\b|\btuin\b|\bjardin\b", features))
        identifier = self._property_id(property_url)
        return {
            "id": identifier,
            "name": name,
            "title": name,
            "url": property_url,
            "price": price,
            "location": location or "",
            "postcode": postcode or "",
            "property_type": self._property_type(property_url),
            "surface_area": surface,
            "bedrooms": rooms,
            "description": description or "",
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
            "image_url_1": images[0] if images else meta("og:image"),
            "image_url_2": images[1] if len(images) > 1 else None,
            "images": images,
            "outdoor_terrace": terrace,
            "outdoor_garden": garden,
        }

    def _find_json_ld(self, soup: BeautifulSoup) -> Dict:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                value = json.loads(script.string or script.get_text())
            except (TypeError, ValueError):
                continue
            values = value if isinstance(value, list) else [value]
            for item in values:
                if isinstance(item, dict) and (item.get("offers") or item.get("address") or item.get("@type") == "Residence"):
                    return item
        return {}

    def _find_next_data(self, soup: BeautifulSoup) -> Dict:
        script = soup.select_one("script#__NEXT_DATA__")
        if not script:
            return {}
        try:
            value = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            return {}
        props = value.get("props", {}).get("pageProps", {}) if isinstance(value, dict) else {}
        for key in ("property", "listing", "propertyData"):
            if isinstance(props.get(key), dict):
                return props[key]
        return props if isinstance(props, dict) else {}

    @staticmethod
    def _meta_content(soup: BeautifulSoup, name: str) -> str:
        element = soup.select_one(f'meta[property="{name}"], meta[name="{name}"]')
        return element.get("content", "").strip() if element else ""

    @staticmethod
    def _property_id(property_url: str) -> str:
        match = re.search(r"/(\d+)$", urlsplit(property_url).path)
        return match.group(1) if match else property_url

    @staticmethod
    def _number(value):
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            cleaned = value.replace("€", "").replace(".", "").replace(",", ".").strip()
            try:
                number = float(cleaned)
                return int(number) if number.is_integer() else number
            except ValueError:
                return value
        return value

    @staticmethod
    def _property_type(property_url: str) -> str:
        match = re.search(r"/(?:nl|fr|en)/(appartement|huis|woning|studio|villa)/", urlsplit(property_url).path, re.I)
        return match.group(1).lower() if match else ""
