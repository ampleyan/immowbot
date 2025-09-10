#!/usr/bin/env python3
"""
Immowbot - Property Market Analysis Tool for Belgium
Scrapes property data from Immoweb.be to help analyze the local property market.
"""

import argparse
from src.scraper import ImmowebScraper
from src.analyzer import PropertyAnalyzer
from src.exporter import DataExporter


def main():
    parser = argparse.ArgumentParser(description='Analyze Belgian property market data')
    parser.add_argument('--search-url', help='Immoweb search URL to scrape')
    parser.add_argument('--max-price', type=int, help='Maximum price filter')
    parser.add_argument('--min-surface', type=int, help='Minimum surface area filter')
    parser.add_argument('--epc-scores', help='EPC scores to include (comma-separated)')
    parser.add_argument('--postal-codes', help='Postal codes to include (comma-separated, e.g. BE-2060,BE-2050)')
    parser.add_argument('--output', default='property_analysis.xlsx', help='Output file name')
    parser.add_argument('--pages', type=int, default=5, help='Number of pages to scrape')
    
    args = parser.parse_args()
    
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
    analyzer = PropertyAnalyzer(properties)
    analysis_results = analyzer.generate_analysis()
    
    # Export results
    exporter = DataExporter()
    exporter.export_to_excel(properties, analysis_results, args.output)
    
    print(f"Analysis exported to {args.output}")


if __name__ == "__main__":
    main()