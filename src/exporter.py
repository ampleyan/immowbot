"""
Data export and visualization functionality.
"""
import re

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any
import os
from datetime import datetime
import numpy as np
import requests
import time
from math import radians, cos, sin, asin, sqrt
from openpyxl.utils import get_column_letter


class DataExporter:
    """Exports property data and analysis results to various formats."""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Reference point: Kronenburgstraat 26
        self.reference_address = "Kronenburgstraat 26"
        self.reference_coordinates = None  # Will be geocoded if needed
        
        # OSRM endpoints - hybrid approach: local for cycling/walking, public for driving
        self.osrm_endpoints = {
            'driving': 'http://router.project-osrm.org/route/v1/driving',  # Public server (reliable)
            'cycling': 'http://localhost:5000/route/v1/cycling',            # Local server (Belgium data)
            'foot': 'http://localhost:5001/route/v1/foot'                   # Try dedicated walking server first
        }
        
        # Fallback endpoints if dedicated servers aren't available
        self.osrm_fallback = {
            'foot': 'http://localhost:5000/route/v1/foot'  # Fallback to cycling server for walking
        }
        
        # Check if local server is available for cycling/walking
        self.local_osrm_available = self._check_local_osrm_server()

    def clean_excel_data(self, df):
        """Remove illegal characters and flatten complex objects from DataFrame for Excel export"""
        if df.empty:
            return df

        # Define illegal characters pattern (control characters, null bytes, etc.)
        illegal_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')

        # Work on a copy to avoid modifying original
        df_clean = df.copy()

        # Get only object columns
        object_columns = df_clean.select_dtypes(include=['object']).columns

        for col in object_columns:
            try:
                df_clean[col] = df_clean[col].apply(self._flatten_complex_value)
                df_clean[col] = df_clean[col].astype(str).apply(
                    lambda x: self._sanitize_excel_string(illegal_chars.sub('', x)) if isinstance(x, str) else x
                )
            except Exception as e:
                print(f"⚠️ Warning: Could not clean column '{col}': {e}")
                # Continue with other columns
                continue

        return df_clean
    
    def _sanitize_excel_string(self, value):
        """Additional sanitization for Excel string values."""
        if not isinstance(value, str):
            return value
        
        # Prevent Excel from interpreting as formula by adding apostrophe prefix
        if value.startswith(('=', '+', '-', '@')):
            value = "'" + value
        
        # Remove line breaks and carriage returns
        value = value.replace('\n', ' ').replace('\r', ' ')
        
        # Truncate if too long (Excel limit is 32,767 characters)
        if len(value) > 32767:
            value = value[:32767]
        
        return value
    
    def _flatten_complex_value(self, value):
        """Convert complex objects (dicts, lists) to string representation for Excel."""
        if isinstance(value, dict):
            if not value:  # Empty dict
                return ""
            # Convert dict to readable string format
            items = []
            for k, v in value.items():
                if isinstance(v, dict):
                    # Nested dict - flatten one level
                    nested_items = [f"{nk}: {nv}" for nk, nv in v.items()]
                    items.append(f"{k}: [{', '.join(nested_items)}]")
                else:
                    items.append(f"{k}: {v}")
            return "; ".join(items)
        elif isinstance(value, list):
            if not value:  # Empty list
                return ""
            # Convert list to string
            return "; ".join(str(item) for item in value)
        else:
            return value
    
    def _create_flattened_dataframe(self, properties):
        """Create a DataFrame with nested dictionaries flattened into separate columns."""
        flattened_properties = []
        
        for prop in properties:
            flattened_prop = {}
            
            # Categories to expand into columns
            detail_categories = [
                'property_details', 'financial_details', 'building_details', 
                'terrain_details', 'location_details', 'layout_details',
                'comfort_details', 'energy_details', 'urban_planning_details',
                'all_property_details'
            ]
            
            for key, value in prop.items():
                if key in detail_categories and isinstance(value, dict):
                    # Flatten this dictionary into columns with prefix
                    prefix = key.replace('_details', '').replace('_', '').upper()
                    
                    if key == 'property_details' and isinstance(value, dict):
                        # Handle the nested structure of property_details
                        for category, details in value.items():
                            if isinstance(details, dict):
                                cat_prefix = f"{prefix}_{category.upper()}"
                                for detail_key, detail_value in details.items():
                                    column_name = f"{cat_prefix}_{detail_key.replace(' ', '_')}"
                                    flattened_prop[column_name] = detail_value
                            else:
                                column_name = f"{prefix}_{category.replace(' ', '_')}"
                                flattened_prop[column_name] = details
                    else:
                        # Handle simple dictionary expansion
                        for detail_key, detail_value in value.items():
                            column_name = f"{prefix}_{detail_key.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')}"
                            flattened_prop[column_name] = detail_value
                else:
                    # Keep non-dictionary values as-is, but flatten simple dicts
                    if isinstance(value, dict) and value:  # Non-empty dict not in categories
                        # Flatten simple dicts into prefixed columns
                        dict_prefix = key.upper()
                        for dict_key, dict_value in value.items():
                            column_name = f"{dict_prefix}_{dict_key.replace(' ', '_')}"
                            flattened_prop[column_name] = dict_value
                    elif isinstance(value, list):
                        # Convert lists to comma-separated strings
                        flattened_prop[key] = "; ".join(str(item) for item in value) if value else ""
                    else:
                        flattened_prop[key] = value
            
            flattened_properties.append(flattened_prop)
        
        return pd.DataFrame(flattened_properties)

    def _sanitize_column_names(self, df):
        """Sanitize DataFrame column names for Excel compatibility."""
        def clean_col(col):
            # Aggressive sanitization for Excel compatibility
            col = str(col)
            # Remove ALL special characters except letters, numbers, and underscores
            col = re.sub(r'[^A-Za-z0-9_]', '_', col)
            # Replace multiple consecutive underscores with single underscore
            col = re.sub(r'_+', '_', col)
            # Remove leading and trailing underscores
            col = col.strip('_')
            # Ensure column name starts with a letter
            if col and not col[0].isalpha():
                col = 'col_' + col
            # Ensure column name is not empty and not too long
            if not col:
                col = 'empty_column'
            elif len(col) > 50:
                col = col[:50]  # Truncate if too long
            return col
        
        # Create new column mapping
        new_columns = {}
        problematic_columns = []
        for col in df.columns:
            original_col = str(col)
            new_col = clean_col(col)
            
            # Debug: check for problematic characters
            if '[' in original_col or ']' in original_col or '(' in original_col or ')' in original_col:
                problematic_columns.append(f"'{original_col}' -> '{new_col}'")
            
            # Handle duplicate column names
            counter = 1
            original_new_col = new_col
            while new_col in new_columns.values():
                new_col = f"{original_new_col}_{counter}"
                counter += 1
            new_columns[col] = new_col
        
        # Debug output (reduced)
        if problematic_columns:
            print(f"⚠️  Found {len(problematic_columns)} problematic column names (cleaned)")
        
        df = df.rename(columns=new_columns)
        return df

    def export_to_excel(self, properties, analysis_results, filename, enable_geo_analysis=False, export_geo_columns=False):
        """Export property data and analysis to Excel file."""
        # Create DataFrame from properties and flatten nested dicts into columns
        df = self._create_flattened_dataframe(properties)

        # Add all_property_details columns (replace if exist)
        all_details_keys = set()
        for prop in properties:
            all_details = prop.get('all_property_details', {})
            if isinstance(all_details, dict):
                all_details_keys.update(all_details.keys())
        all_details_keys = sorted(all_details_keys)

        all_details_dict = {
            key: [prop.get('all_property_details', {}).get(key, '') for prop in properties]
            for key in all_details_keys
        }
        all_details_df = pd.DataFrame(all_details_dict)
        # Sanitize the all_details DataFrame column names before concatenating
        all_details_df = self._sanitize_column_names(all_details_df)
        df = pd.concat([df, all_details_df], axis=1)
        # for key in all_details_keys:
        #     df[key] = [prop.get('all_property_details', {}).get(key, '') for prop in properties]

        # Remove geo columns if not requested
        geo_cols = ['latitude', 'longitude', 'Car_Time', 'Car_Distance', 'Bike_Time', 'Bike_Distance', 'Walk_Time', 'Walk_Distance']
        if not export_geo_columns:
            for col in geo_cols:
                if col in df.columns:
                    df = df.drop(columns=[col])

        # Create Excel writer - using xlsxwriter with enhanced data validation
        try:
            print("📄 Using xlsxwriter engine with enhanced data validation")
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                # Try only the Raw Data sheet first to isolate the issue
                print("📄 Creating Raw Data sheet...")
                df = self.clean_excel_data(df)
                df = self._sanitize_column_names(df)
                df.to_excel(writer, sheet_name='Raw Data', index=False)
                print("✅ Raw Data sheet created successfully")
                
                # Custom property tracking sheet (your requested format)
                print("📄 Creating Property Tracking sheet...")
                self._create_property_tracking_sheet(writer, properties, enable_geo_analysis, export_geo_columns)
                print("✅ Property Tracking sheet created successfully")
                
                # Property Summary sheet (reduced columns)
                print("📄 Creating Property Summary sheet...")
                self._create_property_summary_sheet(writer, properties)
                print("✅ Property Summary sheet created successfully")
                
                # Detailed property information sheet (for Immoscoop comprehensive data)
                print("📄 Creating Detailed Info sheet...")
                self._create_detailed_property_sheet(writer, properties)
                print("✅ Detailed Info sheet created successfully")
                
                # Property details category sheets (Financial, Building, etc.)
                print("📄 Creating category sheets...")
                self._create_property_category_sheets(writer, properties)
                print("✅ Category sheets created successfully")
                
                # Summary sheet
                print("📄 Creating Summary sheet...")
                self._create_summary_sheet(writer, analysis_results)
                print("✅ Summary sheet created successfully")
                
                # Price analysis sheet
                if 'price_analysis' in analysis_results:
                    print("📄 Creating Price Analysis sheet...")
                    self._create_price_analysis_sheet(writer, analysis_results['price_analysis'], df)
                    print("✅ Price Analysis sheet created successfully")
                
                # Location analysis sheet
                if 'location_analysis' in analysis_results:
                    print("📄 Creating Location Analysis sheet...")
                    self._create_location_analysis_sheet(writer, analysis_results['location_analysis'])
                    print("✅ Location Analysis sheet created successfully")
                
                # Postcode analysis sheet
                if 'postcode_analysis' in analysis_results:
                    print("📄 Creating Postcode Analysis sheet...")
                    self._create_postcode_analysis_sheet(writer, analysis_results['postcode_analysis'])
                    print("✅ Postcode Analysis sheet created successfully")
                
                # EPC analysis sheet
                if 'epc_analysis' in analysis_results:
                    print("📄 Creating EPC Analysis sheet...")
                    self._create_epc_analysis_sheet(writer, analysis_results['epc_analysis'])
                    print("✅ EPC Analysis sheet created successfully")
                
                # Feature analysis sheet
                if 'feature_analysis' in analysis_results:
                    print("📄 Creating Feature Analysis sheet...")
                    self._create_feature_analysis_sheet(writer, analysis_results['feature_analysis'])
                    print("✅ Feature Analysis sheet created successfully")
                
                # Geographic analysis sheet
                if 'geographic_analysis' in analysis_results:
                    print("📄 Creating Geographic Analysis sheet...")
                    self._create_geographic_analysis_sheet(writer, analysis_results['geographic_analysis'])
                    print("✅ Geographic Analysis sheet created successfully")
                
                # Market segments sheet
                if 'market_segments' in analysis_results:
                    print("📄 Creating Market Segments sheet...")
                    self._create_market_segments_sheet(writer, analysis_results['market_segments'])
                    print("✅ Market Segments sheet created successfully")
                
                # LLM Analysis sheet
                if 'llm_analysis' in analysis_results:
                    print("📄 Creating LLM Analysis sheet...")
                    self._create_llm_analysis_sheet(writer, analysis_results['llm_analysis'])
                    print("✅ LLM Analysis sheet created successfully")
        except Exception as e:
            print(f"❌ Error during Excel creation: {e}")
            import traceback
            print(f"   Full traceback: {traceback.format_exc()}")
            raise
        
        print(f"Data exported to {filename}")
        
        # Generate visualizations
        self._create_visualizations(df, analysis_results, filename.replace('.xlsx', '_charts.png'))
    
    def _create_summary_sheet(self, writer, analysis_results):
        """Create summary sheet with key statistics."""
        summary_data = []
        
        if 'summary' in analysis_results:
            summary = analysis_results['summary']
            summary_data.append(['Total Properties', summary.get('total_properties', 'N/A')])
            
            if 'price_statistics' in summary:
                price_stats = summary['price_statistics']
                summary_data.extend([
                    ['Mean Price (€)', f"{price_stats.get('mean_price', 0):,.0f}"],
                    ['Median Price (€)', f"{price_stats.get('median_price', 0):,.0f}"],
                    ['Min Price (€)', f"{price_stats.get('min_price', 0):,.0f}"],
                    ['Max Price (€)', f"{price_stats.get('max_price', 0):,.0f}"]
                ])
        
        # Add recommendations
        if 'recommendations' in analysis_results:
            summary_data.append(['', ''])  # Empty row
            summary_data.append(['KEY INSIGHTS', ''])
            for i, rec in enumerate(analysis_results['recommendations'], 1):
                summary_data.append([f'Insight {i}', rec])
        
        summary_df = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    def _create_price_analysis_sheet(self, writer, price_analysis, df):
        """Create price analysis sheet."""
        price_data = []
        
        # Price ranges
        if 'price_ranges' in price_analysis:
            price_data.append(['PRICE RANGES', ''])
            for range_name, count in price_analysis['price_ranges'].items():
                price_data.append([range_name.replace('_', ' ').title(), count])
        
        # Quartiles
        if 'quartiles' in price_analysis:
            price_data.append(['', ''])
            price_data.append(['PRICE QUARTILES', ''])
            quartiles = price_analysis['quartiles']
            price_data.extend([
                ['Q1 (25th percentile)', f"€{quartiles.get('q1', 0):,.0f}"],
                ['Q2 (50th percentile)', f"€{quartiles.get('q2', 0):,.0f}"],
                ['Q3 (75th percentile)', f"€{quartiles.get('q3', 0):,.0f}"]
            ])
        
        # Price per m2
        if 'price_per_m2' in price_analysis:
            price_data.append(['', ''])
            price_data.append(['PRICE PER M²', ''])
            pm2 = price_analysis['price_per_m2']
            price_data.extend([
                ['Mean Price/m²', f"€{pm2.get('mean', 0):.0f}"],
                ['Median Price/m²', f"€{pm2.get('median', 0):.0f}"]
            ])
        
        price_df = pd.DataFrame(price_data, columns=['Metric', 'Value'])
        price_df.to_excel(writer, sheet_name='Price Analysis', index=False)
    
    def _create_location_analysis_sheet(self, writer, location_analysis):
        """Create location analysis sheet."""
        location_data = []
        
        if 'location_distribution' in location_analysis:
            location_data.append(['PROPERTIES BY LOCATION', 'COUNT'])
            for location, count in location_analysis['location_distribution'].items():
                location_data.append([location, count])
        
        if 'location_price_analysis' in location_analysis:
            location_data.append(['', ''])
            location_data.append(['AVERAGE PRICES BY LOCATION', ''])
            location_data.append(['Location', 'Mean Price', 'Median Price', 'Count'])
            
            for location, stats in location_analysis['location_price_analysis'].items():
                location_data.append([
                    location,
                    f"€{stats.get('mean', 0):,.0f}",
                    f"€{stats.get('median', 0):,.0f}",
                    stats.get('count', 0)
                ])
        
        location_df = pd.DataFrame(location_data)
        location_df.to_excel(writer, sheet_name='Location Analysis', index=False, header=False)
    
    def _create_postcode_analysis_sheet(self, writer, postcode_analysis):
        """Create postcode analysis sheet."""
        postcode_data = []
        
        if 'postcode_distribution' in postcode_analysis:
            postcode_data.append(['PROPERTIES BY POSTCODE', 'COUNT'])
            for postcode, count in postcode_analysis['postcode_distribution'].items():
                postcode_data.append([postcode, count])
        
        if 'postcode_price_analysis' in postcode_analysis:
            postcode_data.append(['', ''])
            postcode_data.append(['AVERAGE PRICES BY POSTCODE', ''])
            postcode_data.append(['Postcode', 'Mean Price', 'Median Price', 'Count'])
            
            for postcode, stats in postcode_analysis['postcode_price_analysis'].items():
                postcode_data.append([
                    postcode,
                    f"€{stats.get('mean', 0):,.0f}",
                    f"€{stats.get('median', 0):,.0f}",
                    stats.get('count', 0)
                ])
        
        postcode_df = pd.DataFrame(postcode_data)
        postcode_df.to_excel(writer, sheet_name='Postcode Analysis', index=False, header=False)
    
    def _create_epc_analysis_sheet(self, writer, epc_analysis):
        """Create EPC analysis sheet."""
        epc_data = []
        
        if 'epc_distribution' in epc_analysis:
            epc_data.append(['EPC SCORE DISTRIBUTION', 'COUNT'])
            for epc, count in epc_analysis['epc_distribution'].items():
                epc_data.append([epc, count])
        
        if 'epc_price_analysis' in epc_analysis:
            epc_data.append(['', ''])
            epc_data.append(['AVERAGE PRICES BY EPC SCORE', ''])
            epc_data.append(['EPC Score', 'Mean Price', 'Median Price', 'Count'])
            
            for epc, stats in epc_analysis['epc_price_analysis'].items():
                epc_data.append([
                    epc,
                    f"€{stats.get('mean', 0):,.0f}",
                    f"€{stats.get('median', 0):,.0f}",
                    stats.get('count', 0)
                ])
        
        epc_df = pd.DataFrame(epc_data)
        epc_df.to_excel(writer, sheet_name='EPC Analysis', index=False, header=False)
    
    def _create_visualizations(self, df, analysis_results, filename):
        """Create visualization charts."""
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))  # Changed to 2x3 grid for 6 charts
        fig.suptitle('Property Market Analysis', fontsize=16, fontweight='bold')
        
        # Price distribution histogram
        if 'price' in df.columns and not df['price'].isna().all():
            prices = df['price'].dropna()
            axes[0, 0].hist(prices, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            axes[0, 0].set_title('Price Distribution')
            axes[0, 0].set_xlabel('Price (€)')
            axes[0, 0].set_ylabel('Frequency')
            axes[0, 0].ticklabel_format(style='plain', axis='x')
        
        # EPC score distribution
        if 'epc_score' in df.columns:
            epc_counts = df['epc_score'].value_counts()
            if len(epc_counts) > 0:
                axes[0, 1].bar(epc_counts.index, epc_counts.values, color='lightgreen', alpha=0.7)
                axes[0, 1].set_title('EPC Score Distribution')
                axes[0, 1].set_xlabel('EPC Score')
                axes[0, 1].set_ylabel('Count')
        
        # Price vs Surface Area scatter plot
        if 'price' in df.columns and 'surface_area' in df.columns:
            valid_data = df[['price', 'surface_area']].dropna()
            if len(valid_data) > 0:
                axes[1, 0].scatter(valid_data['surface_area'], valid_data['price'], alpha=0.6, color='coral')
                axes[1, 0].set_title('Price vs Surface Area')
                axes[1, 0].set_xlabel('Surface Area (m²)')
                axes[1, 0].set_ylabel('Price (€)')
                
                # Add trend line
                z = np.polyfit(valid_data['surface_area'], valid_data['price'], 1)
                p = np.poly1d(z)
                axes[1, 0].plot(valid_data['surface_area'], p(valid_data['surface_area']), "r--", alpha=0.8)
        
        # Location distribution (top 10)
        if 'postcode' in df.columns:
            location_counts = df['postcode'].value_counts().head(10)
            if len(location_counts) > 0:
                axes[1, 1].barh(range(len(location_counts)), location_counts.values, color='gold', alpha=0.7)
                axes[1, 1].set_yticks(range(len(location_counts)))
                axes[1, 1].set_yticklabels(location_counts.index)
                axes[1, 1].set_title('Top 10 Postcodes (by Count)')
                axes[1, 1].set_xlabel('Number of Properties')
        
        # Travel time distribution (if travel time data exists)
        travel_time_data = []
        for _, prop in df.iterrows():
            # Try to extract travel time data if it exists
            car_time = str(prop.get('Car_Time', '')).replace('min', '').replace('h', '*60+').replace('m', '')
            if car_time and car_time != 'nan':
                try:
                    # Simple parsing for minutes
                    if '*60+' in car_time:
                        # Handle hours and minutes
                        parts = car_time.split('*60+')
                        minutes = int(parts[0]) * 60 + int(parts[1]) if len(parts) > 1 else int(parts[0]) * 60
                    else:
                        minutes = int(car_time)
                    travel_time_data.append(minutes)
                except (ValueError, AttributeError):
                    pass
        
        if travel_time_data:
            axes[0, 2].hist(travel_time_data, bins=10, alpha=0.7, color='purple', edgecolor='black')
            axes[0, 2].set_title(f'Travel Time to {self.reference_address}')
            axes[0, 2].set_xlabel('Travel Time (minutes)')
            axes[0, 2].set_ylabel('Number of Properties')
        else:
            axes[0, 2].text(0.5, 0.5, 'No travel time\ndata available', 
                           ha='center', va='center', transform=axes[0, 2].transAxes,
                           fontsize=12, style='italic')
            axes[0, 2].set_title(f'Travel Time Distribution')
        
        # Top 5 closest properties to reference address (new chart)
        properties_list = df.to_dict('records')
        closest_properties = self._find_closest_properties(properties_list, top_n=5)
        
        if closest_properties:
                # Prepare data for the chart
                locations = []
                distances = []
                prices = []
                
                for prop in closest_properties:
                    location = prop.get('location', 'Unknown')
                    # Shorten location name if too long
                    if len(location) > 20:
                        location = location[:17] + '...'
                    locations.append(location)
                    distances.append(prop['distance_to_reference'])
                    prices.append(prop.get('price', 0))
                
                # Create bar chart of distances
                colors = ['red', 'orange', 'gold', 'lightgreen', 'lightblue']
                bars = axes[1, 2].bar(range(len(distances)), distances, 
                                    color=colors[:len(distances)], alpha=0.7)
                
                # Add location labels and prices
                for i, (dist, price, loc) in enumerate(zip(distances, prices, locations)):
                    axes[1, 2].text(i, dist + 0.1, f'{loc}\n€{price:,.0f}', 
                                   ha='center', va='bottom', fontsize=8, 
                                   rotation=45 if len(loc) > 10 else 0)
                
                axes[1, 2].set_title(f'Top 5 Closest to\n{self.reference_address}')
                axes[1, 2].set_xlabel('Property Rank')
                axes[1, 2].set_ylabel('Distance (km)')
                axes[1, 2].set_xticks(range(len(distances)))
                axes[1, 2].set_xticklabels([f'#{i+1}' for i in range(len(distances))])
                axes[1, 2].grid(True, alpha=0.3, axis='y')
        else:
                # If no closest properties found, show message
                axes[1, 2].text(0.5, 0.5, 'No properties with\ncoordinate data found', 
                               ha='center', va='center', transform=axes[1, 2].transAxes,
                               fontsize=12, style='italic')
                axes[1, 2].set_title(f'Top 5 Closest to\n{self.reference_address}')
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Visualizations saved to {filename}")
    
    def _geocode_address(self, address):
        """Geocode an address to get latitude and longitude using Nominatim."""
        try:
            # Use OpenStreetMap Nominatim API for geocoding
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': f"{address}, Belgium",
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'PropertyAnalysisBot/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            time.sleep(1)  # Be respectful to Nominatim
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = float(data[0]['lat'])
                    lon = float(data[0]['lon'])
                    return (lat, lon)
        except Exception as e:
            print(f"⚠ Error geocoding {address}: {e}")
        
        return None
    
    def _check_local_osrm_server(self):
        """Check if local OSRM servers are running and test profile availability."""
        cycling_available = False
        walking_server_available = False
        
        # Test cycling server (port 5000)
        try:
            cycling_response = requests.get('http://localhost:5000/route/v1/cycling/4.4,51.2;4.41,51.21', timeout=3)
            if cycling_response.status_code == 200:
                cycling_available = True
        except:
            pass
        
        # Test dedicated walking server (port 5001)
        try:
            foot_response = requests.get('http://localhost:5001/route/v1/foot/4.4,51.2;4.41,51.21', timeout=3)
            if foot_response.status_code == 200:
                walking_server_available = True
        except:
            pass
        
        if cycling_available and walking_server_available:
            print("✅ Local OSRM servers detected: cycling (5000) + walking (5001) - full Belgium OSM data!")
            print("ℹ️  Driving routes will use reliable public server")
            return True
        elif cycling_available:
            print("✅ Local OSRM cycling server detected (port 5000) - using Belgium OSM data!")
            print("ℹ️  Walking will use cycling routes + speed adjustments")
            print("ℹ️  Driving routes will use public server")
            return True
        
        print("ℹ️  No local OSRM servers found - using speed adjustments for cycling/walking")
        print("ℹ️  Driving routes will use public server")
        return False
    
    def _get_reference_coordinates(self):
        """Get coordinates for Kronenburgstraat 26."""
        if self.reference_coordinates is None:
            print(f"🗺️  Geocoding reference address: {self.reference_address}")
            self.reference_coordinates = self._geocode_address(self.reference_address)
            if self.reference_coordinates:
                lat, lon = self.reference_coordinates
                print(f"✅ Reference coordinates: {lat:.6f}, {lon:.6f}")
            else:
                print(f"❌ Could not geocode reference address")
        return self.reference_coordinates
    
    def _calculate_travel_time(self, from_coords, to_coords, profile="driving"):
        """Calculate travel time using OSRM API with realistic speed adjustments."""
        if not from_coords or not to_coords:
            return {"duration_minutes": None, "distance_km": None, "error": "Missing coordinates"}
        
        try:
            from_lat, from_lon = from_coords
            to_lat, to_lon = to_coords
            
            # Hybrid approach: local for cycling/walking, public for driving
            if profile == 'driving':
                # Always use reliable public server for driving
                url = f"http://router.project-osrm.org/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}"
                print(f"   Using public OSRM: {profile} profile")
            elif self.local_osrm_available and profile == 'cycling':
                # Use local server with Belgium OSM data for cycling
                base_url = self.osrm_endpoints[profile]
                url = f"{base_url}/{from_lon},{from_lat};{to_lon},{to_lat}"
                print(f"   Using local OSRM: {profile} profile (Belgium data)")
            elif self.local_osrm_available and profile == 'foot':
                # Try dedicated walking server first (port 5001), fallback to cycling server (port 5000)
                base_url = self.osrm_endpoints[profile]
                try:
                    # Quick test if dedicated walking server is available
                    test_response = requests.get(f"{base_url}/{from_lon},{from_lat};{to_lon},{to_lat}", timeout=2)
                    if test_response.status_code == 200:
                        url = f"{base_url}/{from_lon},{from_lat};{to_lon},{to_lat}"
                        print(f"   Using dedicated walking server: {profile} profile (Belgium pedestrian data)")
                    else:
                        raise Exception("Dedicated walking server not available")
                except:
                    # Fallback to cycling server with walking adjustments
                    fallback_url = self.osrm_fallback[profile]
                    url = f"{fallback_url}/{from_lon},{from_lat};{to_lon},{to_lat}"
                    print(f"   Using cycling server: {profile} profile (Belgium data) + walking adjustments")
            else:
                # Fallback to public server with speed adjustments for cycling/walking
                url = f"http://router.project-osrm.org/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}"
                print(f"   Using public OSRM with {profile} speed adjustments")
            params = {
                'overview': 'false',
                'alternatives': 'false',
                'steps': 'false'
            }
            
            response = requests.get(url, params=params, timeout=15)
            time.sleep(0.5)  # Be respectful to OSRM
            
            if response.status_code == 200:
                data = response.json()
                if data.get('routes'):
                    route = data['routes'][0]
                    duration_seconds = route['duration']  # in seconds
                    distance_meters = route['distance']   # in meters
                    
                    # Apply speed adjustments based on data source
                    # if profile == "driving":
                    #     # Driving always uses public server - use as-is
                    #     duration_seconds = base_duration_seconds
                    #     distance_meters = base_distance_meters
                    # elif self.local_osrm_available and profile == 'cycling':
                    #     # Local server provides real Belgium cycling data - use as-is
                    #     duration_seconds = base_duration_seconds
                    #     distance_meters = base_distance_meters
                    # elif self.local_osrm_available and profile == 'foot':
                    #     # Cycling server + walking speed adjustment
                    #     # Apply walking speed: typically 2.5-3x slower than cycling
                    #     duration_seconds = base_duration_seconds * 2.5
                    #     distance_meters = base_distance_meters * 0.92   # Pedestrians can take more shortcuts
                    # else:
                    #     # Fallback: apply speed adjustments for cycling/walking using driving route
                    #     if profile == "cycling":
                    #         # Cycling in Belgium: ~20-25 km/h average (vs ~50 km/h driving in city)
                    #         duration_seconds = base_duration_seconds * 2.8
                    #         distance_meters = base_distance_meters * 0.95
                    #     elif profile == "foot":
                    #         # Walking: ~5 km/h average (vs ~50 km/h driving in city)
                    #         duration_seconds = base_duration_seconds * 8.5
                    #         distance_meters = base_distance_meters * 0.85
                    #     else:
                    #         duration_seconds = base_duration_seconds
                    #         distance_meters = base_distance_meters
                    #
                    return {
                        "duration_minutes": round(duration_seconds / 60, 1),
                        "distance_km": round(distance_meters / 1000, 1),
                        "error": None,
                        "profile_used": profile
                    }
            else:
                print(f"⚠ OSRM API error for {profile}: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error details: {error_data.get('message', 'Unknown error')}")
                except:
                    pass
                return {"duration_minutes": None, "distance_km": None, "error": f"HTTP {response.status_code}"}
            
            return {"duration_minutes": None, "distance_km": None, "error": "No route found"}
            
        except Exception as e:
            print(f"⚠ Error calculating {profile} route: {e}")
            return {"duration_minutes": None, "distance_km": None, "error": str(e)}
    
    def _get_travel_times_for_property(self, prop):
        """Calculate travel times for different transport modes."""
        # Get property coordinates
        prop_coords = None
        if prop.get('latitude') and prop.get('longitude'):
            prop_coords = (float(prop['latitude']), float(prop['longitude']))
        elif prop.get('coordinates'):
            coords = prop['coordinates']
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                prop_coords = (coords[0], coords[1])
        
        # If no coordinates, try to geocode the address
        if not prop_coords and prop.get('location'):
            print(f"🗺️  Geocoding property: {prop.get('location')}")
            prop_coords = self._geocode_address(prop.get('location'))
        
        reference_coords = self._get_reference_coordinates()
        
        if not prop_coords or not reference_coords:
            return {
                "car_time": "No coordinates",
                "bike_time": "No coordinates", 
                "walk_time": "No coordinates",
                "car_distance": "",
                "bike_distance": "",
                "walk_distance": ""
            }
        
        # Calculate travel times for different modes
        travel_modes = {
            "car": "driving",
            "bike": "cycling", 
            "walk": "foot"
        }
        
        results = {}
        print(f"🚗 Calculating travel times for property...")
        
        for mode_name, osrm_profile in travel_modes.items():
            print(f"   {mode_name.title()} route...")
            try:
                result = self._calculate_travel_time(prop_coords, reference_coords, osrm_profile)
                
                if result["duration_minutes"] and result["duration_minutes"] > 0:
                    # Format time nicely
                    minutes = result["duration_minutes"]
                    if minutes < 60:
                        time_str = f"{minutes:.0f}min"
                    else:
                        hours = int(minutes // 60)
                        mins = int(minutes % 60)
                        time_str = f"{hours}h{mins:02d}min"
                    
                    results[f"{mode_name}_time"] = time_str
                    results[f"{mode_name}_distance"] = f"{result['distance_km']:.1f}km"
                    
                    # Show calculation details for debugging
                    if result.get('base_car_time'):
                        print(f"   ✅ {mode_name.title()}: {time_str}, {result['distance_km']:.1f}km (base car: {result['base_car_time']:.0f}min)")
                    else:
                        print(f"   ✅ {mode_name.title()}: {time_str}, {result['distance_km']:.1f}km")
                        
                else:
                    results[f"{mode_name}_time"] = "No route"
                    results[f"{mode_name}_distance"] = ""
                    print(f"   ❌ {mode_name.title()}: No route found ({result.get('error', 'Unknown error')})")
                    
            except Exception as e:
                print(f"⚠ Error calculating {mode_name} time: {e}")
                results[f"{mode_name}_time"] = "Error"
                results[f"{mode_name}_distance"] = ""
        
        return results
    
    def _calculate_distance_km(self, coord1, coord2):
        """Calculate great circle distance between two points in kilometers."""
        if not coord1 or not coord2:
            return float('inf')
        
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        return c * r
    
    def _find_closest_properties(self, properties, top_n=5):
        """Find the N closest properties to the reference address."""
        reference_coords = self._get_reference_coordinates()
        if not reference_coords:
            return []
        
        properties_with_distance = []
        
        for prop in properties:
            # Get property coordinates
            prop_coords = None
            if prop.get('latitude') and prop.get('longitude'):
                try:
                    prop_coords = (float(prop['latitude']), float(prop['longitude']))
                except (ValueError, TypeError):
                    pass
            
            if not prop_coords and prop.get('coordinates'):
                coords = prop['coordinates']
                if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    try:
                        prop_coords = (float(coords[0]), float(coords[1]))
                    except (ValueError, TypeError):
                        pass
            
            # Calculate distance
            if prop_coords:
                distance = self._calculate_distance_km(prop_coords, reference_coords)
                prop_with_distance = prop.copy()
                prop_with_distance['distance_to_reference'] = distance
                properties_with_distance.append(prop_with_distance)
        
        # Sort by distance and return top N
        properties_with_distance.sort(key=lambda x: x['distance_to_reference'])
        return properties_with_distance[:top_n]

    def _create_property_tracking_sheet(self, writer, properties, enable_geo_analysis=False, export_geo_columns=False):
        """Create custom property tracking sheet with your requested columns."""
        tracking_data = []
        
        # Sort properties by postcode first, then by price
        def sort_key(prop):
            postcode = prop.get('postcode', '')
            # Convert postcode to string and pad with zeros for proper sorting
            postcode_str = str(postcode).zfill(10) if postcode else 'ZZZZZ'
            
            price = prop.get('price', 0)
            # Convert price to number, default to 0 if not available
            try:
                price_num = float(price) if price else 0
            except (ValueError, TypeError):
                price_num = 0
            
            return (postcode_str, price_num)
        
        # Sort the properties
        sorted_properties = sorted(properties, key=sort_key)
        print(f"📋 Sorted {len(properties)} properties by postcode then price")
        
        # Find closest properties for highlighting only if geo analysis is enabled
        closest_properties = []
        closest_urls = set()
        
        if enable_geo_analysis:
            closest_properties = self._find_closest_properties(sorted_properties, top_n=5)
            closest_urls = {prop.get('url', '') for prop in closest_properties}
            
            if closest_properties:
                print(f"\n📍 Top 5 closest properties to {self.reference_address}:")
                for i, prop in enumerate(closest_properties, 1):
                    location = prop.get('location', 'Unknown location')
                    distance = prop['distance_to_reference']
                    price = prop.get('price', 0)
                    print(f"   {i}. {location} - {distance:.1f}km away - €{price:,.0f}")
            else:
                print(f"\n📍 No properties with coordinate data found for distance calculation")
        else:
            print(f"\n🚫 Geolocation analysis disabled - skipping distance calculations")

        # Define logical column groups based on user specification
        amenities = [
            "Garage", "Garden", "Lift", "Balcony", "Cellar", "Double_glazing", "Terrace", "outdoor_terrace"
        ]
        surface_fields = [
            "Surface", "Surface_area_bathroom", "Surface_bedrooms", "Surface_garden", "Surface_kitchen", 
            "Terrace_surface", "Bedroom_surface", "Living_room_surface"
        ]
        property_details = [
            "POSTCODE", "ADDRESS", "Floor", "SURFACE", "Surface", "bedrooms", "PRICE", "EPC", "Kwm_year", "RENOVATION", 
            "bathrooms", "terrain_area", "property_type", "construction_year", "renovation_year", "Renovation_year", 
            "Subtype", "Type_of_property", "State_building", "Availability", "agent_email", "LINK",
            "Bathroom_type", "Construction_year", "Destination_building", "Flood-prone", "Heating_source", 
            "Heating_type", "Kitchen", "Orientation_rear_facade", "Type_of_glazing", "Type_of_kitchen", "Unique_code_EPC"
        ]
        scores = [
            "P-score", "P-score_parcel_score", "G-score_building_score", "E-level", "EPC_label", "EPC_score_kWhm_years"
        ]
        llm_fields = [
            "LLM_CONDITION", "LLM_SUMMARY", "LLM_PROS", "LLM_CONS", "LLM_CONFIDENCE"
        ]
        
        # Combine all groups in the desired order
        base_headers = (
            property_details +
            amenities +
            surface_fields +
            scores +
            llm_fields
        )
        
        # Remove duplicates while preserving order
        seen = set()
        headers = [x for x in base_headers if not (x in seen or seen.add(x))]
        
        # The headers list now contains all the organized columns - no need to add all_details separately
        # since the dynamic mapping will handle them
        # Optionally add geo columns
        geo_cols = ['latitude', 'longitude', 'Car_Time', 'Car_Distance', 'Bike_Time', 'Bike_Distance', 'Walk_Time', 'Walk_Distance']
        if export_geo_columns:
            headers += geo_cols
        
        for prop in sorted_properties:
            # Get travel time data for this property only if enabled
            print(f"\n📍 Processing property: {prop.get('location', 'Unknown')}")
            if enable_geo_analysis:
                travel_times = self._get_travel_times_for_property(prop)
            else:
                # Use empty travel times when geo analysis is disabled
                travel_times = {
                    'car_time': '',
                    'car_distance': '',
                    'bike_time': '',
                    'bike_distance': '',
                    'walk_time': '',
                    'walk_distance': ''
                }
            
            # Extract and format data for each column
            viewing = ''  # Empty for manual input
            address = prop.get('location', prop.get('name', ''))
            postcode = prop.get('postcode', '')
            price = f"€{prop.get('price', 0):,.0f}" if prop.get('price') else ''
            
            # Extract EPC info from all_details if available, fallback to main epc_score
            epc = prop.get('epc_score', '')
            kw_m_year = ''
            
            # Try to get detailed EPC info from all_details
            all_details = prop.get('all_property_details', {})
            if all_details:
                # Prefer EPC label over score for the EPC column
                epc_label = all_details.get('EPC label', '')
                epc_score_kwh = all_details.get('EPC score (kWh/(m² years))', '')
                
                if epc_label:
                    epc = epc_label
                elif epc_score_kwh:
                    epc = f"{epc_score_kwh} kWh/m²"
                
                # Fill in the kWh/m² year column with the detailed score
                if epc_score_kwh:
                    kw_m_year = epc_score_kwh
            
            p_score = ''  # Empty for manual scoring
            renovation = prop.get('building_state', '')
            surface = f"{prop.get('surface_area', '')}m²" if prop.get('surface_area') else ''
            bedrooms = prop.get('bedrooms', '')
            bathrooms = prop.get('bathrooms', '')
            terrain_area = f"{prop.get('terrain_area', '')}m²" if prop.get('terrain_area') else ''
            
            # Travel time data
            car_time = travel_times.get('car_time', '')
            car_distance = travel_times.get('car_distance', '')
            bike_time = travel_times.get('bike_time', '')
            bike_distance = travel_times.get('bike_distance', '')
            walk_time = travel_times.get('walk_time', '')
            walk_distance = travel_times.get('walk_distance', '')

            # New fields
            property_type = prop.get('property_type', '')
            construction_year = prop.get('construction_year', '')
            renovation_year = prop.get('renovation_year', '')
            outdoor_surface = f"{prop.get('outdoor_surface', '')}m²" if prop.get('outdoor_surface') else ''
            energy_type = prop.get('energy_type', '')
            building_state = prop.get('building_state', '')
            kitchen_type = prop.get('kitchen_type', '')
            outdoor_terrace = prop.get('outdoor_terrace', '')
            parking = prop.get('parking', '')
            
            # LLM Analysis data
            llm_condition = prop.get('llm_condition', '')
            llm_summary = prop.get('llm_summary', '')[:200] + '...' if len(prop.get('llm_summary', '')) > 200 else prop.get('llm_summary', '')
            llm_pros = prop.get('llm_pros', '')[:150] + '...' if len(prop.get('llm_pros', '')) > 150 else prop.get('llm_pros', '')
            llm_cons = prop.get('llm_cons', '')[:150] + '...' if len(prop.get('llm_cons', '')) > 150 else prop.get('llm_cons', '')
            llm_confidence = f"{prop.get('llm_confidence', 0):.2f}" if prop.get('llm_confidence') else ''

            doubts = ''  # Empty for manual notes
            agency = prop.get('agent_name', '')
            agent_website = prop.get('agent_website', '')
            agent_email = prop.get('agent_email', '')
            agent_mobile = prop.get('agent_mobile', '')
            agent_phone = prop.get('agent_phone', '')

            contacts = []
            if agent_phone:
                contacts.append(f"Tel: {agent_phone}")
            if agent_email:
                contacts.append(f"Email: {agent_email}")
            if agent_mobile:
                contacts.append(f"Mobile: {agent_mobile}")
            contacts_str = ' | '.join(contacts)

            link = prop.get('url', '')
            data_source = prop.get('data_source', 'html_parsing')

            # All data now handled by dynamic field mapping above
            # Create a dynamic field mapping for flexible column ordering
            def get_field_value(field_name):
                """Get value for a specific field from property data."""
                # Get all available data sources
                all_details = prop.get('all_property_details', {})
                
                # Field mapping - map column names to data extraction logic
                field_mapping = {
                    'Viewing': viewing,
                    'POSTCODE': postcode,
                    'ADDRESS': address,
                    'Floor': prop.get('floor', 'Floor'),
                    'SURFACE': surface,
                    'Surface': all_details.get('Surface', ''),
                    'bedrooms': bedrooms,
                    'PRICE': price,
                    'EPC': epc,
                    'Kwm_year': kw_m_year,
                    'RENOVATION': renovation,
                    'bathrooms': bathrooms,
                    'terrain_area': terrain_area,
                    'property_type': property_type,
                    'construction_year': construction_year,
                    'renovation_year': renovation_year,
                    'Renovation_year': all_details.get('Renovation year', ''),
                    'Subtype': all_details.get('Subtype', ''),
                    'Type_of_property': all_details.get('Type of property', ''),
                    'State_building': all_details.get('State building', ''),
                    'Availability': all_details.get('Availability', ''),
                    'agent_email': agent_email,
                    'LINK': link,
                    'Bathroom_type': all_details.get('Bathroom type', ''),
                    'Construction_year': all_details.get('Construction year', ''),
                    'Destination_building': all_details.get('Destination building', ''),
                    'Flood-prone': all_details.get('Flood-prone', ''),
                    'Heating_source': all_details.get('Heating source', ''),
                    'Heating_type': all_details.get('Heating type', ''),
                    'Kitchen': all_details.get('Kitchen', ''),
                    'Orientation_rear_facade': all_details.get('Orientation rear facade', ''),
                    'Type_of_glazing': all_details.get('Type of glazing', ''),
                    'Type_of_kitchen': all_details.get('Type of kitchen', ''),
                    'Unique_code_EPC': all_details.get('Unique code EPC', ''),
                    # Amenities
                    'Garage': all_details.get('Garage', ''),
                    'Garden': all_details.get('Garden', ''),
                    'Lift': all_details.get('Lift', ''),
                    'Balcony': all_details.get('Balcony', ''),
                    'Cellar': all_details.get('Cellar', ''),
                    'Double_glazing': all_details.get('Double glazing', all_details.get('Type of glazing', '')),
                    'Terrace': all_details.get('Terrace', ''),
                    'outdoor_terrace': outdoor_terrace,
                    # Surface fields  
                    'Surface_area_bathroom': all_details.get('Surface area bathroom', ''),
                    'Surface_bedrooms': all_details.get('Surface bedrooms', ''),
                    'Surface_garden': all_details.get('Surface garden', ''),
                    'Surface_kitchen': all_details.get('Surface kitchen', ''),
                    'Terrace_surface': all_details.get('Terrace surface', ''),
                    'Bedroom_surface': all_details.get('Bedroom surface', ''),
                    'Living_room_surface': all_details.get('Living room surface', ''),
                    # Scores
                    'P-score': all_details.get('P-score (parcel score)', ''),
                    'P-score_parcel_score': all_details.get('P-score (parcel score)', ''),
                    'G-score_building_score': all_details.get('G-score (building score)', ''),
                    'E-level': all_details.get('E-level', ''),
                    'EPC_label': all_details.get('EPC label', ''),
                    'EPC_score_kWhm_years': all_details.get('EPC score (kWh/(m² years))', ''),
                    # LLM fields
                    'LLM_CONDITION': llm_condition,
                    'LLM_SUMMARY': llm_summary,
                    'LLM_PROS': llm_pros,
                    'LLM_CONS': llm_cons,
                    'LLM_CONFIDENCE': llm_confidence,
                    # Additional tracking fields
                    'DOUBTS': doubts,
                    'AGENCY': agency,
                    'agent_website': agent_website,
                    'agent_mobile': agent_mobile,
                    'agent_phone': agent_phone,
                    'CONTACTS': contacts_str,
                    'data_source': data_source,
                    # Geo columns
                    'latitude': prop.get('latitude', ''),
                    'longitude': prop.get('longitude', ''),
                    'Car_Time': travel_times.get('car_time', ''),
                    'Car_Distance': travel_times.get('car_distance', ''),
                    'Bike_Time': travel_times.get('bike_time', ''),
                    'Bike_Distance': travel_times.get('bike_distance', ''),
                    'Walk_Time': travel_times.get('walk_time', ''),
                    'Walk_Distance': travel_times.get('walk_distance', ''),
                }
                
                # Return the mapped value, or try direct lookup in all_details, or empty string
                return field_mapping.get(field_name, all_details.get(field_name, ''))
            
            # Build row data dynamically based on headers
            row = []
            for header in headers:
                row.append(get_field_value(header))
            tracking_data.append(row)

        # Create DataFrame and export
        tracking_df = pd.DataFrame(tracking_data, columns=headers)
        
        # Additional data sanitization to ensure no list objects remain in data
        for col in tracking_df.columns:
            tracking_df[col] = tracking_df[col].apply(
                lambda x: str(x) if isinstance(x, (list, dict)) else x
            )
        
        tracking_df = self._sanitize_column_names(tracking_df)
        # Sort by postcode (as string, to preserve leading zeros)  
        if 'POSTCODE' in tracking_df.columns:
            tracking_df = tracking_df.sort_values(by='POSTCODE', key=lambda x: x.astype(str).str.zfill(10), ignore_index=True)
        tracking_df.to_excel(writer, sheet_name='Property Tracking', index=False)

        worksheet = writer.sheets['Property Tracking']

        # Adjust column widths (updated to include travel time columns)
        column_widths = {
            'A': 10,  # Viewing
            'B': 40,  # ADDRESS
            'C': 10,  # POSTCODE
            'D': 12,  # PRICE
            'E': 8,   # EPC
            'F': 12,  # Kw/m year
            'G': 10,  # P-score
            'H': 15,  # RENOVATION
            'I': 10,  # SURFACE
            'J': 10,  # bedrooms
            'K': 12,  # Car_Time
            'L': 12,  # Car_Distance
            'M': 12,  # Bike_Time
            'N': 12,  # Bike_Distance
            'O': 12,  # Walk_Time
            'P': 12,  # Walk_Distance
            'Q': 15,  # property_type
            'R': 15,  # construction_year
            'S': 15,  # outdoor_surface
            'T': 12,  # energy_type
            'U': 20,  # coordinates
            'V': 12,  # latitude
            'W': 12,  # longitude
            'X': 15,  # building_state
            'Y': 15,  # kitchen_type
            'Z': 15,  # outdoor_terrace
            'AA': 10, # parking
            'AB': 15, # LLM_CONDITION
            'AC': 40, # LLM_SUMMARY
            'AD': 30, # LLM_PROS
            'AE': 30, # LLM_CONS
            'AF': 10, # LLM_CONFIDENCE
            'AG': 20, # DOUBTS
            'AH': 20, # AGENCY
            'AI': 30, # agent_website
            'AJ': 30, # agent_email
            'AK': 15, # agent_mobile
            'AL': 15, # agent_phone
            'AM': 40, # CONTACTS
            'AN': 50, # LINK
        }
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.hyperlink import Hyperlink


        # Skip all formatting and column width setting to avoid openpyxl column reference issues
        print("⚠️  Skipping Excel formatting to avoid column reference errors")
        
        print(f"✅ Property tracking sheet created with {len(closest_properties)} closest properties highlighted in green")
    
    def _create_property_summary_sheet(self, writer, properties):
        """Create a simplified Property Summary sheet with essential columns only."""
        # Define the essential columns in the specified order
        essential_columns = [
            "LINK", "POSTCODE", "ADDRESS","street","PRICE",  "Floor", "Surface", "bedrooms", "Surface_bedrooms",
            "Bathroom_type", "Surface_area_bathroom", "Heating_source", "Heating_type", 
            "Kitchen", "Type_of_glazing", "Type_of_kitchen", "EPC",
            "EPC_label", "EPC_score_kWhm_years", "Kwm_year", "P-score", "P-score_parcel_score", 
            "G-score_building_score", "Garage", "Garden", "Lift", "Balcony",
            "Cellar",  "Terrace","LLM_CONDITION","LLM_SUMMARY",	"LLM_PROS",	"LLM_CONS",	"LLM_CONFIDENCE"
        ]
        
        # Create data rows
        summary_data = []
        
        for prop in properties:
            all_details = prop.get('all_property_details', {})
            
            def get_value_case_insensitive(field_name):
                """Get value with case-insensitive matching."""
                
                # Special handling for Surface/SURFACE - should contain same data
                if field_name.upper() in ['SURFACE', 'SURFACE']:
                    surface_area = prop.get('surface_area', '')
                    if surface_area:
                        return f"{surface_area}m²"
                    # Fallback to all_details Surface field
                    return all_details.get('Surface', '')
                
                # Field mapping with case-insensitive lookup
                field_mapping = {
                    'LINK': prop.get('url', ''),
                    'POSTCODE': prop.get('postcode', ''),
                    'ADDRESS': prop.get('location', prop.get('name', '')),
                    'STREET': prop.get('street', ''),
                    'PRICE': f"€{prop.get('price', 0):,.0f}" if prop.get('price') else '',
                    'FLOOR': prop.get('floor', all_details.get('Floor', '')),
                    'SURFACE': f"{prop.get('surface_area', '')}m²" if prop.get('surface_area') else all_details.get('Surface', ''),
                    'BEDROOMS': prop.get('bedrooms', ''),
                    'SURFACE_BEDROOMS': all_details.get('Surface bedrooms', ''),
                    'BATHROOM_TYPE': all_details.get('Bathroom type', ''),
                    'SURFACE_AREA_BATHROOM': all_details.get('Surface area bathroom', ''),
                    'HEATING_SOURCE': all_details.get('Heating source', ''),
                    'HEATING_TYPE': all_details.get('Heating type', ''),
                    'KITCHEN': all_details.get('Kitchen', ''),
                    'TYPE_OF_GLAZING': all_details.get('Type of glazing', ''),
                    'TYPE_OF_KITCHEN': all_details.get('Type of kitchen', ''),
                    'EPC': all_details.get('EPC label', prop.get('epc_score', '')),
                    'E-LEVEL': all_details.get('E-level', ''),
                    'EPC_LABEL': all_details.get('EPC label', ''),
                    'EPC_SCORE_KWHM_YEARS': all_details.get('EPC score (kWh/(m² years))', ''),
                    'KWM_YEAR': all_details.get('EPC score (kWh/(m² years))', ''),
                    'P-SCORE': all_details.get('P-score (parcel score)', ''),
                    'P-SCORE_PARCEL_SCORE': all_details.get('P-score (parcel score)', ''),
                    'G-SCORE_BUILDING_SCORE': all_details.get('G-score (building score)', ''),
                    'GARAGE': all_details.get('Garage', ''),
                    'GARDEN': all_details.get('Garden', ''),
                    'LIFT': all_details.get('Lift', ''),
                    'BALCONY': all_details.get('Balcony', ''),
                    'CELLAR': all_details.get('Cellar', ''),
                    'DOUBLE_GLAZING': all_details.get('Double glazing', all_details.get('Type of glazing', '')),
                    'TERRACE': all_details.get('Terrace', ''),
                    'OUTDOOR_TERRACE': prop.get('outdoor_terrace', ''),
                    # LLM Analysis fields
                    'LLM_CONDITION': prop.get('llm_condition', ''),
                    'LLM_SUMMARY': prop.get('llm_summary', '')[:200] + '...' if len(prop.get('llm_summary', '')) > 200 else prop.get('llm_summary', ''),
                    'LLM_PROS': prop.get('llm_pros', '')[:150] + '...' if len(prop.get('llm_pros', '')) > 150 else prop.get('llm_pros', ''),
                    'LLM_CONS': prop.get('llm_cons', '')[:150] + '...' if len(prop.get('llm_cons', '')) > 150 else prop.get('llm_cons', ''),
                    'LLM_CONFIDENCE': f"{prop.get('llm_confidence', 0):.2f}" if prop.get('llm_confidence') else '',
                }
                
                # Try exact match first, then case-insensitive
                if field_name in field_mapping:
                    return field_mapping[field_name]
                
                # Case-insensitive lookup
                field_upper = field_name.upper()
                if field_upper in field_mapping:
                    return field_mapping[field_upper]
                
                # Try direct lookup in all_details with case variations
                for key in all_details:
                    if key.upper() == field_upper:
                        return all_details[key]
                
                return ''
            
            # Build row data
            row = []
            for column in essential_columns:
                row.append(get_value_case_insensitive(column))
            
            summary_data.append(row)
        
        # Create DataFrame and apply sanitization
        summary_df = pd.DataFrame(summary_data, columns=essential_columns)
        summary_df = self.clean_excel_data(summary_df)
        summary_df = self._sanitize_column_names(summary_df)
        
        # Sort by postcode then price
        if 'POSTCODE' in summary_df.columns:
            summary_df = summary_df.sort_values(by='POSTCODE', key=lambda x: x.astype(str).str.zfill(10), ignore_index=True)
        
        # Export to Excel
        summary_df.to_excel(writer, sheet_name='Property Summary', index=False)
    
    def _create_feature_analysis_sheet(self, writer, feature_analysis):
        """Create feature analysis sheet."""
        feature_data = []
        
        # Building states
        if 'building_states' in feature_analysis:
            feature_data.append(['BUILDING STATES', 'Count'])
            for state, count in feature_analysis['building_states'].items():
                feature_data.append([state, count])
            feature_data.append(['', ''])
        
        # Kitchen types
        if 'kitchen_types' in feature_analysis:
            feature_data.append(['KITCHEN TYPES', 'Count'])
            for kitchen, count in feature_analysis['kitchen_types'].items():
                feature_data.append([kitchen, count])
            feature_data.append(['', ''])
        
        # Amenities
        if 'amenities' in feature_analysis:
            amenities = feature_analysis['amenities']
            for amenity in ['outdoor_terrace', 'parking']:
                if amenity in amenities:
                    feature_data.append([f'{amenity.replace("_", " ").title()}', 'Count'])
                    for value, count in amenities[amenity].items():
                        feature_data.append([str(value), count])
                    feature_data.append(['', ''])
        
        # Energy types
        if 'energy_types' in feature_analysis:
            feature_data.append(['ENERGY TYPES', 'Count'])
            for energy_type, count in feature_analysis['energy_types'].items():
                feature_data.append([energy_type, count])
        
        if feature_data:
            feature_df = pd.DataFrame(feature_data, columns=['Feature', 'Value'])
            feature_df = self._sanitize_column_names(feature_df)
            feature_df.to_excel(writer, sheet_name='Feature Analysis', index=False)
    
    def _create_geographic_analysis_sheet(self, writer, geo_analysis):
        """Create geographic analysis sheet."""
        geo_data = []
        
        # Province analysis
        if 'province_distribution' in geo_analysis:
            geo_data.append(['PROVINCES', 'Count'])
            for province, count in geo_analysis['province_distribution'].items():
                geo_data.append([province, count])
            geo_data.append(['', ''])
        
        # Most expensive cities
        if 'most_expensive_cities' in geo_analysis:
            geo_data.append(['MOST EXPENSIVE CITIES', 'Median Price (€)'])
            for city, stats in geo_analysis['most_expensive_cities'].items():
                geo_data.append([city, f"€{stats.get('median', 0):,.0f}"])
            geo_data.append(['', ''])
        
        # Most affordable cities
        if 'most_affordable_cities' in geo_analysis:
            geo_data.append(['MOST AFFORDABLE CITIES', 'Median Price (€)'])
            for city, stats in geo_analysis['most_affordable_cities'].items():
                geo_data.append([city, f"€{stats.get('median', 0):,.0f}"])
            geo_data.append(['', ''])
        
        # Coordinate bounds
        if 'coordinate_bounds' in geo_analysis:
            bounds = geo_analysis['coordinate_bounds']
            geo_data.append(['GEOGRAPHIC BOUNDS', 'Value'])
            geo_data.extend([
                ['North Boundary', f"{bounds.get('north', 0):.6f}"],
                ['South Boundary', f"{bounds.get('south', 0):.6f}"],
                ['East Boundary', f"{bounds.get('east', 0):.6f}"],
                ['West Boundary', f"{bounds.get('west', 0):.6f}"],
                ['Center Latitude', f"{bounds.get('center_lat', 0):.6f}"],
                ['Center Longitude', f"{bounds.get('center_lng', 0):.6f}"]
            ])
        
        if geo_data:
            geo_df = pd.DataFrame(geo_data, columns=['Location', 'Value'])
            geo_df = self._sanitize_column_names(geo_df)
            geo_df.to_excel(writer, sheet_name='Geographic Analysis', index=False)
    
    def _create_market_segments_sheet(self, writer, market_analysis):
        """Create market segments analysis sheet."""
        market_data = []
        
        # Price segments
        if 'price_segments' in market_analysis:
            market_data.append(['PRICE SEGMENTS', 'Count'])
            for segment, count in market_analysis['price_segments'].items():
                market_data.append([segment, count])
            market_data.append(['', ''])
        
        # Property type analysis
        if 'property_type_analysis' in market_analysis:
            market_data.append(['PROPERTY TYPES', 'Count', 'Avg Price (€)', 'Median Price (€)'])
            for prop_type, stats in market_analysis['property_type_analysis'].items():
                price_stats = stats.get('price', {})
                market_data.append([
                    prop_type,
                    price_stats.get('count', 0),
                    f"€{price_stats.get('mean', 0):,.0f}",
                    f"€{price_stats.get('median', 0):,.0f}"
                ])
        
        if market_data:
            market_df = pd.DataFrame(market_data, columns=['Segment', 'Count', 'Avg Price', 'Median Price'])
            market_df = self._sanitize_column_names(market_df)
            market_df.to_excel(writer, sheet_name='Market Segments', index=False)
    
    def _create_llm_analysis_sheet(self, writer, llm_analysis):
        """Create LLM analysis summary sheet."""
        if 'error' in llm_analysis:
            # Create simple error sheet
            error_df = pd.DataFrame([['Error', llm_analysis['error']]], columns=['Status', 'Message'])
            error_df.to_excel(writer, sheet_name='LLM Analysis', index=False)
            return
        
        llm_data = []
        
        # Overall LLM summary
        if 'llm_summary' in llm_analysis:
            summary = llm_analysis['llm_summary']
            llm_data.append(['LLM ANALYSIS SUMMARY', ''])
            llm_data.append(['Total Properties Analyzed', summary.get('total_properties_analyzed', 0)])
            llm_data.append(['Average Confidence Score', f"{summary.get('average_confidence', 0):.2f}"])
            llm_data.append(['Model Used', summary.get('model_used', 'Unknown')])
            llm_data.append(['', ''])
        
        # Condition distribution
        if 'condition_distribution' in llm_analysis:
            llm_data.append(['PROPERTY CONDITIONS', 'Count'])
            for condition, count in llm_analysis['condition_distribution'].items():
                llm_data.append([condition.title(), count])
            llm_data.append(['', ''])
        
        # Confidence statistics
        if 'confidence_stats' in llm_analysis:
            stats = llm_analysis['confidence_stats']
            llm_data.append(['CONFIDENCE STATISTICS', 'Value'])
            llm_data.extend([
                ['Mean Confidence', f"{stats.get('mean', 0):.3f}"],
                ['Median Confidence', f"{stats.get('median', 0):.3f}"],
                ['Min Confidence', f"{stats.get('min', 0):.3f}"],
                ['Max Confidence', f"{stats.get('max', 0):.3f}"],
                ['Low Confidence Properties (<0.5)', stats.get('low_confidence_count', 0)]
            ])
            llm_data.append(['', ''])
        
        # Insights summary
        if 'insights' in llm_analysis:
            insights = llm_analysis['insights']
            llm_data.append(['KEY INSIGHTS', 'Count'])
            llm_data.extend([
                ['High Confidence Properties (>70%)', insights.get('high_confidence_properties', 0)],
                ['Excellent Condition Properties', insights.get('excellent_condition_count', 0)],
                ['Potential Good Value Properties', insights.get('potential_good_value_count', 0)],
                ['Properties Needing Work', insights.get('needs_work_count', 0)]
            ])
            llm_data.append(['', ''])
        
        # Top-rated properties
        if 'insights' in llm_analysis and 'top_rated_properties' in llm_analysis['insights']:
            llm_data.append(['TOP RATED PROPERTIES', ''])
            llm_data.append(['Location', 'Price', 'Condition', 'Confidence', 'Summary'])
            
            for prop in llm_analysis['insights']['top_rated_properties'][:5]:
                llm_data.append([
                    prop.get('location', 'Unknown'),
                    f"€{prop.get('price', 0):,}" if prop.get('price') else '',
                    prop.get('condition', ''),
                    f"{prop.get('confidence', 0):.2f}",
                    prop.get('summary', '')
                ])
            llm_data.append(['', ''])
        
        # Common themes
        if 'common_themes' in llm_analysis:
            themes = llm_analysis['common_themes']
            
            # Frequent pros
            if 'frequent_pros' in themes and themes['frequent_pros']:
                llm_data.append(['MOST COMMON POSITIVE FEATURES', 'Frequency'])
                for keyword, count in themes['frequent_pros'].items():
                    llm_data.append([keyword.title(), count])
                llm_data.append(['', ''])
            
            # Frequent cons
            if 'frequent_cons' in themes and themes['frequent_cons']:
                llm_data.append(['MOST COMMON CONCERNS', 'Frequency'])
                for keyword, count in themes['frequent_cons'].items():
                    llm_data.append([keyword.title(), count])
                llm_data.append(['', ''])
            
            # Red flags
            if 'common_red_flags' in themes and themes['common_red_flags']:
                llm_data.append(['COMMON RED FLAGS', 'Frequency'])
                for keyword, count in themes['common_red_flags'].items():
                    llm_data.append([keyword.title(), count])
        
        if llm_data:
            llm_df = pd.DataFrame(llm_data)
            llm_df = self._sanitize_column_names(llm_df)
            llm_df.to_excel(writer, sheet_name='LLM Analysis', index=False, header=False)
    
    def _create_detailed_property_sheet(self, writer, properties):
        """Create detailed property information sheet for Immoscoop comprehensive data."""
        detailed_data = []
        
        # Check if we have properties with detailed information
        has_detailed_info = any(prop.get('property_details') for prop in properties)
        
        if not has_detailed_info:
            # Create a simple note if no detailed info available
            detailed_data = [
                ['Detailed Property Information', ''],
                ['', ''],
                ['No detailed property information available.', ''],
                ['This sheet will contain comprehensive property details', ''],
                ['when scraping from websites that provide detailed information', ''],
                ['like Immoscoop.be property_detail_groups.', '']
            ]
        else:
            detailed_data.append(['COMPREHENSIVE PROPERTY DETAILS', ''])
            detailed_data.append(['', ''])
            
            # Process each property with detailed information
            for prop in properties:
                if not prop.get('property_details'):
                    continue
                    
                # Property header
                property_name = prop.get('name', prop.get('location', 'Unknown Property'))
                detailed_data.append([f"PROPERTY: {property_name}", ''])
                detailed_data.append(['URL', prop.get('url', '')])
                detailed_data.append(['Price', f"€{prop.get('price', 0):,.0f}" if prop.get('price') else ''])
                detailed_data.append(['', ''])
                
                property_details = prop.get('property_details', {})
                
                # Add each category of details
                category_order = ['financial', 'building', 'terrain', 'location', 'layout', 'comfort', 'energy', 'urban_planning']
                
                for category in category_order:
                    category_data = property_details.get(category, {})
                    if category_data:
                        detailed_data.append([f"{category.upper().replace('_', ' ')}", ''])
                        for detail_title, detail_value in category_data.items():
                            detailed_data.append([f"  {detail_title}", detail_value])
                        detailed_data.append(['', ''])
                
                # Add separator between properties
                detailed_data.append(['='*50, ''])
                detailed_data.append(['', ''])
        
        # Create DataFrame and export
        detailed_df = pd.DataFrame(detailed_data, columns=['Detail', 'Value'])
        detailed_df = self._sanitize_column_names(detailed_df)
        detailed_df.to_excel(writer, sheet_name='Detailed Info', index=False)
    
    def _create_property_category_sheets(self, writer, properties):
        """Create separate Excel sheets for each property detail category."""
        
        # Define categories to create sheets for
        categories = {
            'financial': 'Financial Details',
            'building': 'Building Details', 
            'terrain': 'Terrain Details',
            'layout': 'Layout Details',
            'comfort': 'Comfort Details',
            'energy': 'Energy Details',
            'urban_planning': 'Urban Planning'
        }
        
        for category_key, sheet_name in categories.items():
            category_data = []
            
            # Check if any properties have this category data
            has_category_data = any(
                prop.get('property_details', {}).get(category_key) 
                for prop in properties
            )
            
            if not has_category_data:
                continue  # Skip empty categories
            
            # Collect all unique fields across all properties for this category
            all_fields = set()
            for prop in properties:
                category_details = prop.get('property_details', {}).get(category_key, {})
                if isinstance(category_details, dict):
                    all_fields.update(category_details.keys())
            
            if not all_fields:
                continue  # Skip if no fields found
            
            # Create header row
            headers = ['Property_Name', 'Address', 'Price', 'URL'] + sorted(list(all_fields))
            
            # Add data rows
            for prop in properties:
                category_details = prop.get('property_details', {}).get(category_key, {})
                if not isinstance(category_details, dict):
                    continue
                
                # Basic property info
                property_name = prop.get('name', prop.get('title', 'Unknown Property'))
                address = prop.get('location', prop.get('address', ''))
                price = f"€{prop.get('price', 0):,.0f}" if prop.get('price') else ''
                url = prop.get('url', '')
                
                # Create row with basic info + category details
                row = [property_name, address, price, url]
                
                # Add values for each field (empty string if not present)
                for field in sorted(all_fields):
                    value = category_details.get(field, '')
                    row.append(value)
                
                category_data.append(row)
            
            # Create DataFrame and export to sheet
            if category_data:
                category_df = pd.DataFrame(category_data, columns=headers)
                category_df = self.clean_excel_data(category_df)
                category_df = self._sanitize_column_names(category_df)
                category_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Auto-adjust column widths for better readability (skip for xlsxwriter compatibility)
                try:
                    worksheet = writer.sheets[sheet_name]
                    for col_num, column in enumerate(category_df.columns, 1):
                        max_length = max(
                            category_df[column].astype(str).apply(len).max(),
                            len(str(column))
                        )
                        # Set a reasonable maximum width
                        adjusted_width = min(max_length + 2, 50)
                        # xlsxwriter uses different API than openpyxl
                        if hasattr(worksheet, 'set_column'):
                            # xlsxwriter API
                            worksheet.set_column(col_num - 1, col_num - 1, adjusted_width)
                        elif hasattr(worksheet, 'column_dimensions'):
                            # openpyxl API
                            worksheet.column_dimensions[chr(64 + col_num)].width = adjusted_width
                except Exception as e:
                    print(f"⚠️  Could not set column widths for {sheet_name}: {e}")
    
    def export_to_csv(self, properties, filename):
        """Export property data to CSV file."""
        df = pd.DataFrame(properties)
        df.to_csv(filename, index=False)
        print(f"Data exported to CSV: {filename}")