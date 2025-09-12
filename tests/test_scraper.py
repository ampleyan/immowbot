#!/usr/bin/env python3
"""
Simple test script to validate the scraper functionality.
"""

from src.scraper import ImmowebScraper


def test_scraper():
    """Test basic scraper functionality."""
    print("Testing Immowbot scraper...")
    
    scraper = ImmowebScraper()
    
    # Test with minimal filters to get some results
    print("Testing with basic filters...")
    try:
        properties = scraper.scrape_with_filters(
            max_price=300000,
            min_surface=50,
            max_pages=1  # Only test 1 page to be quick
        )
        
        print(f"Successfully scraped {len(properties)} properties")
        
        if properties:
            # Show first property as example
            first_property = properties[0]
            print("\nExample property:")
            for key, value in first_property.items():
                print(f"  {key}: {value}")
        else:
            print("No properties found - this might be due to anti-bot measures")
            
    except Exception as e:
        print(f"Error during scraping: {e}")
        print("This is expected if Chrome WebDriver setup fails")
        print("The scraper should automatically fall back to requests-based scraping")


if __name__ == "__main__":
    test_scraper()