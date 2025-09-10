#!/usr/bin/env python3
"""
JSON Property Analysis Tool
Analyze existing property data from JSON files without re-scraping.
"""

import argparse
import json
import os
import sys
from src.analyzer import PropertyAnalyzer
from src.exporter import DataExporter


def list_available_json_files():
    """List all JSON files in the current directory."""
    json_files = [f for f in os.listdir('.') if f.endswith('.json')]
    if json_files:
        print("📁 Available JSON files:")
        for i, filename in enumerate(json_files, 1):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        count = len(data)
                        print(f"   {i}. {filename} ({count} properties)")
                    else:
                        print(f"   {i}. {filename} (not a property list)")
            except:
                print(f"   {i}. {filename} (unable to read)")
    else:
        print("❌ No JSON files found in current directory.")
    
    return json_files


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


def show_property_summary(properties: list):
    """Show a quick summary of the loaded properties."""
    if not properties:
        return
    
    print(f"\n📊 Quick Summary:")
    print(f"   Total properties: {len(properties)}")
    
    # Show sample fields available
    if properties:
        sample_prop = properties[0]
        available_fields = list(sample_prop.keys())
        print(f"   Available fields: {', '.join(available_fields[:10])}{'...' if len(available_fields) > 10 else ''}")
    
    # Show price range if available
    prices = [p.get('price') for p in properties if p.get('price') and isinstance(p.get('price'), (int, float))]
    if prices:
        print(f"   Price range: €{min(prices):,.0f} - €{max(prices):,.0f}")
    
    # Show locations if available
    locations = [p.get('location') for p in properties if p.get('location')]
    unique_locations = list(set(locations))
    if unique_locations:
        print(f"   Locations: {len(unique_locations)} unique areas")


def interactive_mode():
    """Interactive mode for selecting and analyzing JSON files."""
    print("🏠 IMMOWBOT JSON ANALYZER")
    print("=" * 50)
    
    json_files = list_available_json_files()
    
    if not json_files:
        print("\n💡 Tip: Run the scraper first to generate JSON files:")
        print("   python main.py --postal-codes BE-2060,BE-2050 --pages 3")
        return
    
    print(f"\nEnter the number (1-{len(json_files)}) or filename:")
    choice = input("Your choice: ").strip()
    
    # Handle numeric choice
    if choice.isdigit():
        choice_num = int(choice)
        if 1 <= choice_num <= len(json_files):
            filename = json_files[choice_num - 1]
        else:
            print(f"❌ Invalid choice. Please select 1-{len(json_files)}")
            return
    else:
        # Handle filename choice
        filename = choice if choice.endswith('.json') else f"{choice}.json"
    
    # Load and analyze
    properties = load_properties_from_json(filename)
    
    if not properties:
        return
    
    show_property_summary(properties)
    
    # Ask for output filename
    default_output = filename.replace('.json', '_analysis.xlsx')
    output_file = input(f"\nOutput filename (default: {default_output}): ").strip()
    if not output_file:
        output_file = default_output
    
    # Ensure .xlsx extension
    if not output_file.endswith('.xlsx'):
        output_file += '.xlsx'
    
    print(f"\n🔄 Analyzing {len(properties)} properties...")
    
    try:
        # Analyze data
        analyzer = PropertyAnalyzer(properties)
        analysis_results = analyzer.generate_analysis()
        
        # Export results
        exporter = DataExporter()
        exporter.export_to_excel(properties, analysis_results, output_file)
        
        print(f"\n✅ Analysis completed!")
        print(f"📊 Excel report: {output_file}")
        print(f"📈 Charts: {output_file.replace('.xlsx', '_charts.png')}")
        
        # Show quick insights
        if 'recommendations' in analysis_results:
            print(f"\n💡 Quick Insights:")
            for rec in analysis_results['recommendations'][:3]:
                print(f"   • {rec}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description='Analyze existing property JSON files')
    parser.add_argument('json_file', nargs='?', help='JSON file to analyze')
    parser.add_argument('--output', help='Output Excel filename')
    parser.add_argument('--list', action='store_true', help='List available JSON files')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    
    args = parser.parse_args()
    
    if args.list:
        list_available_json_files()
        return
    
    if args.interactive or not args.json_file:
        interactive_mode()
        return
    
    # Direct file analysis mode
    properties = load_properties_from_json(args.json_file)
    
    if not properties:
        return
    
    show_property_summary(properties)
    
    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        output_file = args.json_file.replace('.json', '_analysis.xlsx')
    
    if not output_file.endswith('.xlsx'):
        output_file += '.xlsx'
    
    print(f"\n🔄 Analyzing {len(properties)} properties...")
    
    try:
        # Analyze data
        analyzer = PropertyAnalyzer(properties)
        analysis_results = analyzer.generate_analysis()
        
        # Export results
        exporter = DataExporter()
        exporter.export_to_excel(properties, analysis_results, output_file)
        
        print(f"\n✅ Analysis completed!")
        print(f"📊 Excel report: {output_file}")
        print(f"📈 Charts: {output_file.replace('.xlsx', '_charts.png')}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")


if __name__ == "__main__":
    main()