#!/usr/bin/env python3
"""
Simple runner script for property analysis with better error handling.
"""

import sys
import traceback
from src.scraper import ImmowebScraper
from src.analyzer import PropertyAnalyzer
from src.exporter import DataExporter


def run_analysis_with_postal_codes():
    """Run analysis with postal code filtering as shown in your example."""
    print("="*60)
    print("Immowbot - Belgian Property Market Analysis")
    print("="*60)
    
    try:
        # Initialize scraper
        scraper = ImmowebScraper()
        print("✓ Scraper initialized")
        
        # Test the postal codes from your example
        postal_codes = ["BE-2060", "BE-2050", "BE-2140", "BE-2020", "BE-2018", "BE-2000"]
        
        print(f"Searching properties in postal codes: {', '.join(postal_codes)}")
        print("Filters: Max price €230,000, Min surface 80m², EPC A++/A+/A/B")
        print("Pages: 2 (for testing)")
        
        # Scrape with filters
        properties = scraper.scrape_with_filters(
            max_price=230000,
            min_surface=80,
            epc_scores=["A++", "A+", "A", "B"],
            postal_codes=postal_codes,
            max_pages=2  # Limited for testing
        )
        
        print(f"✓ Scraped {len(properties)} properties")
        
        if not properties:
            print("⚠ No properties found. This could be due to:")
            print("  - Very specific filters (try broader criteria)")
            print("  - Anti-bot measures on the website") 
            print("  - Network issues")
            return
        
        # Analyze data
        print("Analyzing property data...")
        analyzer = PropertyAnalyzer(properties)
        analysis_results = analyzer.generate_analysis()
        print("✓ Analysis completed")
        
        # Export results
        print("Exporting results...")
        exporter = DataExporter()
        output_file = "antwerp_properties_analysis.xlsx"
        exporter.export_to_excel(properties, analysis_results, output_file)
        print(f"✓ Results exported to {output_file}")
        
        # Show summary
        if 'summary' in analysis_results and 'price_statistics' in analysis_results['summary']:
            stats = analysis_results['summary']['price_statistics']
            print("\n" + "="*40)
            print("QUICK SUMMARY")
            print("="*40)
            print(f"Properties found: {len(properties)}")
            if stats:
                print(f"Average price: €{stats.get('mean_price', 0):,.0f}")
                print(f"Median price: €{stats.get('median_price', 0):,.0f}")
                print(f"Price range: €{stats.get('min_price', 0):,.0f} - €{stats.get('max_price', 0):,.0f}")
            
            if 'recommendations' in analysis_results:
                print("\nKey Insights:")
                for i, rec in enumerate(analysis_results['recommendations'][:3], 1):
                    print(f"{i}. {rec}")
        
    except KeyboardInterrupt:
        print("\n⚠ Analysis interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"✗ Error during analysis: {e}")
        print("\nFull error details:")
        traceback.print_exc()
        print("\nTips for troubleshooting:")
        print("1. Make sure Chrome browser is installed")
        print("2. Check your internet connection")
        print("3. Try running: pip install -r requirements.txt")
        print("4. Try with broader filters (higher max-price, lower min-surface)")
        sys.exit(1)


if __name__ == "__main__":
    run_analysis_with_postal_codes()