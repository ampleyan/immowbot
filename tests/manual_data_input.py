#!/usr/bin/env python3
"""
Manual data input tool for when scraping fails.
Allows users to manually enter property data from Immoweb.be for analysis.
"""

import json
from typing import List, Dict
from src.analyzer import PropertyAnalyzer
from src.exporter import DataExporter


def get_property_data() -> Dict:
    """Get property data from user input."""
    print("\n" + "="*50)
    print("MANUAL PROPERTY DATA ENTRY")
    print("="*50)
    print("Enter property details (press Enter to skip optional fields):")
    
    property_data = {}
    
    # Required fields
    property_data['url'] = input("Property URL: ").strip()
    
    # Price
    price_input = input("Price (€, numbers only, e.g. 200000): ").strip()
    try:
        property_data['price'] = float(price_input) if price_input else None
    except ValueError:
        property_data['price'] = None
        print("Invalid price format, skipping...")
    
    # Location and postcode
    property_data['location'] = input("Location (e.g. Antwerp, 2060): ").strip() or None
    postcode = input("Postcode (4 digits, e.g. 2060): ").strip()
    property_data['postcode'] = postcode if postcode.isdigit() and len(postcode) == 4 else None
    
    # Surface area
    surface_input = input("Surface area (m², numbers only, e.g. 85): ").strip()
    try:
        property_data['surface_area'] = float(surface_input) if surface_input else None
    except ValueError:
        property_data['surface_area'] = None
        print("Invalid surface area, skipping...")
    
    # EPC score
    epc = input("EPC score (A++, A+, A, B, C, D, E, F, G): ").strip().upper()
    property_data['epc_score'] = epc if epc in ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G'] else None
    
    # Property type
    prop_type = input("Property type (House/Apartment): ").strip().title()
    property_data['property_type'] = prop_type if prop_type in ['House', 'Apartment'] else None
    
    # Bedrooms
    bedrooms_input = input("Number of bedrooms: ").strip()
    try:
        property_data['bedrooms'] = int(bedrooms_input) if bedrooms_input else None
    except ValueError:
        property_data['bedrooms'] = None
    
    # Construction year
    year_input = input("Construction year (e.g. 1995): ").strip()
    try:
        year = int(year_input) if year_input else None
        property_data['construction_year'] = year if year and 1800 <= year <= 2025 else None
    except ValueError:
        property_data['construction_year'] = None
    
    return property_data


def manual_data_entry_mode():
    """Interactive manual data entry mode."""
    properties = []
    
    print("MANUAL DATA ENTRY MODE")
    print("When automatic scraping fails, you can manually enter property data here.")
    print("You can find properties on: https://www.immoweb.be")
    print("\nTip: Open Immoweb.be in your browser, search with your criteria, and enter data from each property")
    
    while True:
        property_data = get_property_data()
        
        # Show summary
        print("\nProperty summary:")
        for key, value in property_data.items():
            if value is not None:
                print(f"  {key}: {value}")
        
        # Confirm
        confirm = input("\nSave this property? (y/n): ").strip().lower()
        if confirm == 'y':
            properties.append(property_data)
            print(f"✓ Property saved. Total properties: {len(properties)}")
        
        # Continue?
        another = input("\nAdd another property? (y/n): ").strip().lower()
        if another != 'y':
            break
    
    if not properties:
        print("No properties entered.")
        return
    
    print(f"\nAnalyzing {len(properties)} properties...")
    
    # Analyze and export
    try:
        analyzer = PropertyAnalyzer(properties)
        analysis_results = analyzer.generate_analysis()
        
        exporter = DataExporter()
        filename = "manual_property_analysis.xlsx"
        exporter.export_to_excel(properties, analysis_results, filename)
        
        print(f"✓ Analysis completed and exported to {filename}")
        
        # Show quick summary
        if 'summary' in analysis_results and 'price_statistics' in analysis_results['summary']:
            stats = analysis_results['summary']['price_statistics']
            print(f"\nQuick Summary:")
            print(f"Properties: {len(properties)}")
            if stats and stats.get('mean_price'):
                print(f"Average price: €{stats.get('mean_price', 0):,.0f}")
                print(f"Median price: €{stats.get('median_price', 0):,.0f}")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        # Save raw data as backup
        with open('manual_properties_backup.json', 'w') as f:
            json.dump(properties, f, indent=2)
        print("Raw data saved to manual_properties_backup.json")


def load_from_json():
    """Load properties from a JSON file."""
    filename = input("Enter JSON filename (or press Enter for manual_properties_backup.json): ").strip()
    if not filename:
        filename = "manual_properties_backup.json"
    
    try:
        with open(filename, 'r') as f:
            properties = json.load(f)
        
        print(f"Loaded {len(properties)} properties from {filename}")
        
        # Analyze
        analyzer = PropertyAnalyzer(properties)
        analysis_results = analyzer.generate_analysis()
        
        exporter = DataExporter()
        output_filename = filename.replace('.json', '_analysis.xlsx')
        exporter.export_to_excel(properties, analysis_results, output_filename)
        
        print(f"Analysis exported to {output_filename}")
        
    except FileNotFoundError:
        print(f"File {filename} not found.")
    except Exception as e:
        print(f"Error loading file: {e}")


def main():
    """Main menu for manual data input."""
    print("IMMOWBOT - MANUAL DATA INPUT")
    print("="*40)
    print("Choose an option:")
    print("1. Manual property data entry")
    print("2. Load properties from JSON file")
    print("3. Exit")
    
    choice = input("\nYour choice (1-3): ").strip()
    
    if choice == '1':
        manual_data_entry_mode()
    elif choice == '2':
        load_from_json()
    elif choice == '3':
        print("Goodbye!")
    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()