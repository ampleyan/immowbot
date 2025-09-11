#!/usr/bin/env python3
"""
Immowbot - Property Market Analysis Tool for Belgium
Scrapes property data from Immoweb.be to help analyze the local property market.
"""

import argparse
import json
import os
from src.scraper import ImmowebScraper
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
    
    args = parser.parse_args()
    
    # Load properties from JSON or scrape new data
    if args.from_json:
        properties = load_properties_from_json(args.from_json)
        print(f"Loaded {len(properties)} properties from {args.from_json}")
    else:
        # Initialize scraper
        scraper = ImmowebScraper()
        
        # Scrape property data
        if args.search_url:
            properties = scraper.scrape_from_url(args.search_url, max_pages=args.pages)
        else:
            properties = scraper.scrape_with_filters(
                max_price=args.max_price,
                min_surface=args.min_surface,
                epc_scores=args.epc_scores.split(',') if args.epc_scores else None,
                postal_codes=args.postal_codes.split(',') if args.postal_codes else None,
                max_pages=args.pages
            )
        
        print(f"Scraped {len(properties)} properties")
    
    # Analyze data
    enable_llm = not args.disable_llm
    if enable_llm:
        if args.llm_speed_mode:
            print("🤖 LLM analysis enabled with SPEED MODE - faster but less detailed analysis")
        else:
            print("🤖 LLM analysis enabled - will analyze property descriptions with local Ollama")
    else:
        print("🚫 LLM analysis disabled")
    
    analyzer = PropertyAnalyzer(properties, enable_llm_analysis=enable_llm, llm_speed_mode=args.llm_speed_mode, model_name='phi3:3.8b')
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