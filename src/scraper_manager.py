"""
Scraper manager for coordinating multiple Belgian real estate scrapers.
"""
from typing import List, Dict, Optional, Union
from .scrapers.immoweb_scraper import ImmowebScraper
from .scrapers.immoscoop_scraper import ImmoscoopScraper
from .scrapers.zimmo_scraper import ZimmoScraper
from .scrapers.realo_scraper import RealoScraper
from .scrapers.immovlan_scraper import ImmovlanScraper
from .base_scraper import BasePropertyScraper


class ScraperManager:
    """Manager class for coordinating multiple real estate scrapers."""
    
    # Available scrapers
    SCRAPERS = {
        'immoweb': ImmowebScraper,
        'immoscoop': ImmoscoopScraper,
        'zimmo': ZimmoScraper,
        'realo': RealoScraper,
        'immovlan': ImmovlanScraper,
    }
    
    def __init__(self):
        self.active_scrapers = {}
    
    def get_available_websites(self) -> List[str]:
        """Get list of available website scrapers."""
        return list(self.SCRAPERS.keys())
    
    def get_scraper(self, website: str) -> BasePropertyScraper:
        """Get scraper instance for a specific website."""
        if website not in self.SCRAPERS:
            raise ValueError(f"Unknown website '{website}'. Available: {', '.join(self.SCRAPERS.keys())}")
        
        if website not in self.active_scrapers:
            self.active_scrapers[website] = self.SCRAPERS[website]()
        
        return self.active_scrapers[website]
    
    def scrape_website(self, website: str,min_price: Optional[int] = None,  max_price: Optional[int] = None,
                      min_surface: Optional[int] = None, epc_scores: Optional[List[str]] = None,
                      postal_codes: Optional[List[str]] = None, max_pages: int = 5,
                      search_url: Optional[str] = None, on_listing=None, on_checked=None,
                      should_cancel=None) -> List[Dict]:
        """Scrape a specific website with filters."""
        scraper = self.get_scraper(website)
        scraper.allowed_postcodes = postal_codes
        
        print(f"\n🌐 Starting {website.title()} scraper...")
        
        if search_url:
            return scraper.scrape_from_url(
                search_url,
                max_pages,
                on_listing=on_listing,
                on_checked=on_checked,
                should_cancel=should_cancel,
            )
        else:
            return scraper.scrape_with_filters(
                max_price=max_price,
                # min_price=min_price,
                min_surface=min_surface,
                epc_scores=epc_scores,
                postal_codes=postal_codes,
                max_pages=max_pages,
                on_listing=on_listing,
                on_checked=on_checked,
                should_cancel=should_cancel,
            )
    
    def scrape_multiple_websites(self, websites: List[str], max_price: Optional[int] = None,
                                min_surface: Optional[int] = None, epc_scores: Optional[List[str]] = None,
                                postal_codes: Optional[List[str]] = None, max_pages: int = 5) -> Dict[str, List[Dict]]:
        """Scrape multiple websites with the same filters."""
        all_results = {}
        
        print(f"\n🚀 Starting multi-website scraping: {', '.join(websites)}")
        
        for website in websites:
            try:
                properties = self.scrape_website(
                    website=website,
                    max_price=max_price,
                    min_surface=min_surface,
                    epc_scores=epc_scores,
                    postal_codes=postal_codes,
                    max_pages=max_pages
                )
                all_results[website] = properties
                print(f"✅ {website.title()}: {len(properties)} properties scraped")
                
            except Exception as e:
                print(f"❌ {website.title()}: Failed to scrape - {e}")
                all_results[website] = []
        
        return all_results

    def scrape_selected_listings(self, selections, on_listing=None, on_checked=None, should_cancel=None):
        if not selections:
            return []
        source = selections[0]["source"]
        scraper = self.get_scraper(source)
        driver = None
        results = []
        try:
            driver = scraper._setup_chrome_driver()
            stealth = getattr(scraper, "_apply_advanced_stealth_mode", None)
            if callable(stealth):
                stealth(driver)
            for selection in selections:
                if should_cancel and should_cancel():
                    break
                raw = scraper._scrape_property_details(selection["url"], driver)
                if raw:
                    normalized = scraper._normalize_property_data(raw)
                    normalized["id"] = str(selection["source_listing_id"])
                    normalized["source"] = source
                    normalized["source_listing_id"] = str(selection["source_listing_id"])
                    normalized["url"] = selection["url"]
                    results.append(normalized)
                    if on_listing:
                        on_listing(normalized)
                if on_checked:
                    on_checked()
        finally:
            if driver:
                driver.quit()
        return results
    
    def combine_results(self, results: Dict[str, List[Dict]]) -> List[Dict]:
        """Combine results from multiple websites into a single list."""
        combined = []
        
        for website, properties in results.items():
            for prop in properties:
                # Ensure source_website is set
                if 'source_website' not in prop:
                    prop['source_website'] = website
                combined.append(prop)
        
        print(f"\n📊 Combined results: {len(combined)} total properties from {len(results)} websites")
        
        # Sort by price for consistent output
        combined.sort(key=lambda x: x.get('price', 0))
        
        return combined
    
    def scrape_all_websites(self, max_price: Optional[int] = None, min_surface: Optional[int] = None,
                           epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None,
                           max_pages: int = 5) -> List[Dict]:
        """Scrape all available websites and combine results."""
        all_websites = self.get_available_websites()
        results = self.scrape_multiple_websites(
            websites=all_websites,
            max_price=max_price,
            min_surface=min_surface,
            epc_scores=epc_scores,
            postal_codes=postal_codes,
            max_pages=max_pages
        )
        
        return self.combine_results(results)
    
    def get_scraper_stats(self) -> Dict[str, Dict]:
        """Get statistics about all active scrapers."""
        stats = {}
        
        for website, scraper in self.active_scrapers.items():
            properties = scraper.get_all_properties()
            stats[website] = {
                'total_properties': len(properties),
                'avg_price': sum(p.get('price', 0) for p in properties) / len(properties) if properties else 0,
                'price_range': {
                    'min': min(p.get('price', 0) for p in properties) if properties else 0,
                    'max': max(p.get('price', 0) for p in properties) if properties else 0
                },
                'locations': len(set(p.get('postcode', '') for p in properties if p.get('postcode')))
            }
        
        return stats
    
    def export_all_to_json(self) -> Dict[str, str]:
        """Export all scraped data to JSON files."""
        exported_files = {}
        
        for website, scraper in self.active_scrapers.items():
            if scraper.get_all_properties():
                filename = scraper.export_to_json()
                exported_files[website] = filename
        
        return exported_files
    
    def clear_all_scrapers(self):
        """Clear all scraped data from all scrapers."""
        for scraper in self.active_scrapers.values():
            scraper.clear_properties()
        
        print("🧹 Cleared all scraper data")
    
    @staticmethod
    def detect_website_from_url(url: str) -> Optional[str]:
        """Detect which website scraper to use based on URL."""
        url_lower = url.lower()
        
        if 'immoweb.be' in url_lower:
            return 'immoweb'
        elif 'immoscoop.be' in url_lower:
            return 'immoscoop'
        elif 'zimmo.be' in url_lower:
            return 'zimmo'
        elif 'realo.be' in url_lower:
            return 'realo'
        elif 'immovlan.be' in url_lower:
            return 'immovlan'
        else:
            return None
    
    @staticmethod
    def validate_filters(max_price: Optional[int] = None, min_price: Optional[int] = None,min_surface: Optional[int] = None,
                        epc_scores: Optional[List[str]] = None, postal_codes: Optional[List[str]] = None) -> bool:
        """Validate filter parameters."""
        if max_price is not None and max_price <= 0:
            print("❌ Max price must be positive")
            return False
        
        if min_surface is not None and min_surface <= 0:
            print("❌ Min surface must be positive")
            return False
        
        if epc_scores:
            valid_scores = ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']
            for score in epc_scores:
                clean_score = score.replace('BE-', '').strip()
                if clean_score not in valid_scores:
                    print(f"❌ Invalid EPC score: {score}. Valid scores: {', '.join(valid_scores)}")
                    return False
        
        if postal_codes:
            for code in postal_codes:
                clean_code = code.replace('BE-', '').strip()
                # if not (clean_code.isdigit() and len(clean_code) == 4):
                #     print(f"❌ Invalid postal code: {code}. Must be 4-digit Belgian postal code")
                #     return False
        
        return True


class ScraperFactory:
    """Factory class for creating scraper instances."""
    
    @staticmethod
    def create_scraper(website: str) -> BasePropertyScraper:
        """Create a scraper instance for the specified website."""
        scrapers = {
            'immoweb': ImmowebScraper,
            'immoscoop': ImmoscoopScraper,
            'zimmo': ZimmoScraper,
            'realo': RealoScraper,
            'immovlan': ImmovlanScraper,
        }
        
        if website.lower() not in scrapers:
            available = ', '.join(scrapers.keys())
            raise ValueError(f"Unknown website '{website}'. Available: {available}")
        
        return scrapers[website.lower()]()
    
    @staticmethod
    def get_available_scrapers() -> Dict[str, str]:
        """Get information about available scrapers."""
        return {
            'immoweb': 'Immoweb.be - Belgium\'s largest real estate platform',
            'immoscoop': 'Immoscoop.be - Belgian real estate with exclusive listings',
            'zimmo': 'Zimmo.be - Belgian real estate platform',
            'realo': 'Realo.be - Belgian real estate platform',
            'immovlan': 'Immovlan.be - Belgian real estate platform'
        }
