#!/usr/bin/env python3
"""
Immowbot - Property Market Analysis Tool for Belgium
Scrapes property data from Immoweb.be to help analyze the local property market.
"""

import argparse
import json
import os
from src.scraper_manager import ScraperManager, ScraperFactory
from src.analyzer import PropertyAnalyzer
from src.exporter import DataExporter


def main():
    parser = argparse.ArgumentParser(description='Analyze Belgian property market data')
    
    # Mode selection
    parser.add_argument('--from-json', help='Analyze properties from existing JSON file instead of scraping')
    
    # Scraping parameters
    parser.add_argument('--search-url', help='Immoweb search URL to scrape')
    parser.add_argument('--max-price', type=int, help='Maximum price filter')
    parser.add_argument('--min-surface', type=int, help='Minimum surface area filter')
    parser.add_argument('--epc-scores', help='EPC scores to include (comma-separated)')
    parser.add_argument('--postal-codes', help='Postal codes to include (comma-separated, e.g. BE-2060,BE-2050)')
    parser.add_argument('--pages', type=int, default=5, help='Number of pages to scrape')
    
    # Output parameters
    parser.add_argument('--output', default='property_analysis.xlsx', help='Output file name')
    parser.add_argument('--disable-llm', action='store_true', help='Disable LLM analysis of property descriptions')
    parser.add_argument('--llm-speed-mode', action='store_true', help='Use faster LLM settings (shorter timeouts, less detailed analysis)')
    parser.add_argument('--enable-geo-analysis', action='store_true', help='Enable geolocation analysis (travel times and distances)')
    
    # Website selection parameters
    parser.add_argument('--website', choices=['immoweb', 'immoscoop', 'zimmo', 'all'], 
                        default='immoweb', help='Website to scrape (default: immoweb)')
    parser.add_argument('--websites', nargs='+', choices=['immoweb', 'immoscoop', 'zimmo'],
                        help='Multiple websites to scrape (alternative to --website)')
    parser.add_argument('--list-websites', action='store_true', help='List available websites and exit')
    
    args = parser.parse_args()
    
    # Initialize scraper manager
    scraper_manager = ScraperManager()
    
    # Handle list websites command
    if args.list_websites:
        print("📋 Available websites:")
        for website, description in ScraperFactory.get_available_scrapers().items():
            print(f"   • {website}: {description}")
        return
    
    # Load properties from JSON or scrape new data
    if args.from_json:
        properties = load_properties_from_json(args.from_json)
        print(f"Loaded {len(properties)} properties from {args.from_json}")
    else:
        # Determine which websites to scrape
        websites_to_scrape = []
        
        if args.websites:
            # Multiple websites specified
            websites_to_scrape = args.websites
        elif args.website == 'all':
            # Scrape all available websites
            websites_to_scrape = scraper_manager.get_available_websites()
        else:
            # Single website specified
            websites_to_scrape = [args.website]
        
        print(f"🌐 Target websites: {', '.join(websites_to_scrape)}")
        
        # Validate filters before scraping
        if not scraper_manager.validate_filters(
            max_price=args.max_price,
            min_surface=args.min_surface,
            epc_scores=args.epc_scores.split(',') if args.epc_scores else None,
            postal_codes=args.postal_codes.split(',') if args.postal_codes else None
        ):
            print("❌ Invalid filter parameters")
            return
        
        # Scrape property data
        if args.search_url:
            # For search URL, detect website automatically
            detected_website = scraper_manager.detect_website_from_url(args.search_url)
            if detected_website:
                print(f"🔍 Detected website from URL: {detected_website}")
                properties = scraper_manager.scrape_website(
                    website=detected_website,
                    search_url=args.search_url,
                    max_pages=args.pages
                )
            else:
                print("❌ Could not detect website from URL. Please specify --website parameter.")
                return
        else:
            # Scrape with filters
            if len(websites_to_scrape) == 1:
                # Single website
                properties = scraper_manager.scrape_website(
                    website=websites_to_scrape[0],
                    max_price=args.max_price,
                    min_surface=args.min_surface,
                    epc_scores=args.epc_scores.split(',') if args.epc_scores else None,
                    postal_codes=args.postal_codes.split(',') if args.postal_codes else None,
                    max_pages=args.pages
                )
            else:
                # Multiple websites
                results = scraper_manager.scrape_multiple_websites(
                    websites=websites_to_scrape,
                    max_price=args.max_price,
                    min_surface=args.min_surface,
                    epc_scores=args.epc_scores.split(',') if args.epc_scores else None,
                    postal_codes=args.postal_codes.split(',') if args.postal_codes else None,
                    max_pages=args.pages
                )
                properties = scraper_manager.combine_results(results)
        
        print(f"\n📊 Total scraped: {len(properties)} properties from {len(websites_to_scrape)} website(s)")
        
        # Show stats per website if multiple websites were used
        if len(websites_to_scrape) > 1:
            stats = scraper_manager.get_scraper_stats()
            for website, website_stats in stats.items():
                if website_stats['total_properties'] > 0:
                    print(f"   • {website.title()}: {website_stats['total_properties']} properties (avg: €{website_stats['avg_price']:,.0f})")
    
    # Analyze data
    enable_llm = not args.disable_llm
    if enable_llm:
        if args.llm_speed_mode:
            print("🤖 LLM analysis enabled with SPEED MODE - faster but less detailed analysis")
        else:
            print("🤖 LLM analysis enabled - will analyze property descriptions with local Ollama")
    else:
        print("🚫 LLM analysis disabled")
    if len(properties)>0:
        analyzer = PropertyAnalyzer(properties, enable_llm_analysis=enable_llm, llm_speed_mode=args.llm_speed_mode, model_name='mistral:7b')
        analysis_results = analyzer.generate_analysis()
    
    # Export results
        exporter = DataExporter()
        if args.enable_geo_analysis:
            print("🗺️ Geolocation analysis enabled - calculating travel times and distances")
        else:
            print("🚫 Geolocation analysis disabled - skipping travel time calculations")
        exporter.export_to_excel(properties, analysis_results, args.output, enable_geo_analysis=args.enable_geo_analysis)
    
    print(f"Analysis exported to {args.output}")


def load_properties_from_json(json_file: str) -> list:
    """Load properties from a JSON file."""
    if not os.path.exists(json_file):
        print(f"❌ Error: JSON file '{json_file}' not found.")
        return []
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            properties = json.load(f)
        
        if not isinstance(properties, list):
            print(f"❌ Error: JSON file should contain a list of properties.")
            return []
        
        print(f"✅ Successfully loaded {len(properties)} properties from {json_file}")
        return properties
    
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}")
        return []
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return []


if __name__ == "__main__":
    main()