"""
Data export and visualization functionality.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any
import os
from datetime import datetime
import numpy as np


class DataExporter:
    """Exports property data and analysis results to various formats."""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def export_to_excel(self, properties: List[Dict], analysis_results: Dict[str, Any], filename: str):
        """Export property data and analysis to Excel file."""
        # Create DataFrame from properties
        df = pd.DataFrame(properties)
        
        # Create Excel writer
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Custom property tracking sheet (your requested format)
            self._create_property_tracking_sheet(writer, properties)
            
            # Raw data sheet
            df.to_excel(writer, sheet_name='Raw Data', index=False)
            
            # Summary sheet
            self._create_summary_sheet(writer, analysis_results)
            
            # Price analysis sheet
            if 'price_analysis' in analysis_results:
                self._create_price_analysis_sheet(writer, analysis_results['price_analysis'], df)
            
            # Location analysis sheet
            if 'location_analysis' in analysis_results:
                self._create_location_analysis_sheet(writer, analysis_results['location_analysis'])
            
            # Postcode analysis sheet
            if 'postcode_analysis' in analysis_results:
                self._create_postcode_analysis_sheet(writer, analysis_results['postcode_analysis'])
            
            # EPC analysis sheet
            if 'epc_analysis' in analysis_results:
                self._create_epc_analysis_sheet(writer, analysis_results['epc_analysis'])
            
            # Feature analysis sheet
            if 'feature_analysis' in analysis_results:
                self._create_feature_analysis_sheet(writer, analysis_results['feature_analysis'])
            
            # Geographic analysis sheet
            if 'geographic_analysis' in analysis_results:
                self._create_geographic_analysis_sheet(writer, analysis_results['geographic_analysis'])
            
            # Market segments sheet
            if 'market_segments' in analysis_results:
                self._create_market_segments_sheet(writer, analysis_results['market_segments'])
        
        print(f"Data exported to {filename}")
        
        # Generate visualizations
        self._create_visualizations(df, analysis_results, filename.replace('.xlsx', '_charts.png'))
    
    def _create_summary_sheet(self, writer: pd.ExcelWriter, analysis_results: Dict[str, Any]):
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
    
    def _create_price_analysis_sheet(self, writer: pd.ExcelWriter, price_analysis: Dict[str, Any], df: pd.DataFrame):
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
    
    def _create_location_analysis_sheet(self, writer: pd.ExcelWriter, location_analysis: Dict[str, Any]):
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
    
    def _create_postcode_analysis_sheet(self, writer: pd.ExcelWriter, postcode_analysis: Dict[str, Any]):
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
    
    def _create_epc_analysis_sheet(self, writer: pd.ExcelWriter, epc_analysis: Dict[str, Any]):
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
    
    def _create_visualizations(self, df: pd.DataFrame, analysis_results: Dict[str, Any], filename: str):
        """Create visualization charts."""
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
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
        if 'location' in df.columns:
            location_counts = df['location'].value_counts().head(10)
            if len(location_counts) > 0:
                axes[1, 1].barh(range(len(location_counts)), location_counts.values, color='gold', alpha=0.7)
                axes[1, 1].set_yticks(range(len(location_counts)))
                axes[1, 1].set_yticklabels(location_counts.index)
                axes[1, 1].set_title('Top 10 Locations (by Count)')
                axes[1, 1].set_xlabel('Number of Properties')
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Visualizations saved to {filename}")

    def _create_property_tracking_sheet(self, writer: pd.ExcelWriter, properties: List[Dict]):
        """Create custom property tracking sheet with your requested columns."""
        tracking_data = []

        headers = ['Viewing', 'ADDRESS', 'PRICE', 'EPC', 'Kw/m year', 'P-score', 'RENOVATION',
                   'SURFACE', 'bedrooms', 'property_type', 'construction_year', 'outdoor_surface',
                   'energy_type', 'coordinates', 'latitude', 'longitude', 'building_state',
                   'kitchen_type', 'outdoor_terrace', 'parking', 'DOUBTS', 'AGENCY', 'agent_website',
                   'agent_email', 'agent_mobile', 'agent_phone', 'CONTACTS', 'LINK']

        for prop in properties:
            # Extract and format data for each column
            viewing = ''  # Empty for manual input
            address = prop.get('location', prop.get('name', ''))
            price = f"€{prop.get('price', 0):,.0f}" if prop.get('price') else ''
            epc = prop.get('epc_score', '')
            kw_m_year = ''  # Will need to be calculated/researched
            p_score = ''  # Empty for manual scoring
            renovation = prop.get('building_state', '')
            surface = f"{prop.get('surface_area', '')}m²" if prop.get('surface_area') else ''
            bedrooms = prop.get('bedrooms', '')

            # New fields
            property_type = prop.get('property_type', '')
            construction_year = prop.get('construction_year', '')
            outdoor_surface = f"{prop.get('outdoor_surface', '')}m²" if prop.get('outdoor_surface') else ''
            energy_type = prop.get('energy_type', '')
            coordinates = f"{prop.get('latitude', '')}, {prop.get('longitude', '')}" if prop.get(
                'latitude') and prop.get('longitude') else ''
            latitude = prop.get('latitude', '')
            longitude = prop.get('longitude', '')
            building_state = prop.get('building_state', '')
            kitchen_type = prop.get('kitchen_type', '')
            outdoor_terrace = prop.get('outdoor_terrace', '')
            parking = prop.get('parking', '')

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

            row = [
                viewing, address, price, epc, kw_m_year, p_score, renovation,
                surface, bedrooms, property_type, construction_year, outdoor_surface,
                energy_type, coordinates, latitude, longitude, building_state,
                kitchen_type, outdoor_terrace, parking, doubts, agency, agent_website,
                agent_email, agent_mobile, agent_phone, contacts_str, link
            ]
            tracking_data.append(row)

        # Create DataFrame and export
        tracking_df = pd.DataFrame(tracking_data, columns=headers)
        tracking_df.to_excel(writer, sheet_name='Property Tracking', index=False)

        # Format the sheet for better readability
        worksheet = writer.sheets['Property Tracking']

        # Adjust column widths (updated to include new columns)
        column_widths = {
            'A': 10,  # Viewing
            'B': 40,  # ADDRESS
            'C': 12,  # PRICE
            'D': 8,  # EPC
            'E': 12,  # Kw/m year
            'F': 10,  # P-score
            'G': 15,  # RENOVATION
            'H': 10,  # SURFACE
            'I': 10,  # bedrooms
            'J': 15,  # property_type
            'K': 15,  # construction_year
            'L': 15,  # outdoor_surface
            'M': 12,  # energy_type
            'N': 20,  # coordinates
            'O': 12,  # latitude
            'P': 12,  # longitude
            'Q': 15,  # building_state
            'R': 15,  # kitchen_type
            'S': 15,  # outdoor_terrace
            'T': 10,  # parking
            'U': 20,  # DOUBTS
            'V': 20,  # AGENCY
            'W': 30,  # agent_website
            'X': 30,  # agent_email
            'Y': 15,  # agent_mobile
            'Z': 15,  # agent_phone
            'AA': 40,  # CONTACTS
            'AB': 50,  # LINK
        }

        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width

        # Add formatting
        from openpyxl.styles import Font, PatternFill, Alignment

        # Header formatting
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")

        for cell in worksheet[1]:  # First row (headers)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        print("✅ Property tracking sheet created with custom columns")
    
    def _create_feature_analysis_sheet(self, writer: pd.ExcelWriter, feature_analysis: Dict[str, Any]):
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
            feature_df.to_excel(writer, sheet_name='Feature Analysis', index=False)
    
    def _create_geographic_analysis_sheet(self, writer: pd.ExcelWriter, geo_analysis: Dict[str, Any]):
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
            geo_df.to_excel(writer, sheet_name='Geographic Analysis', index=False)
    
    def _create_market_segments_sheet(self, writer: pd.ExcelWriter, market_analysis: Dict[str, Any]):
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
            market_df.to_excel(writer, sheet_name='Market Segments', index=False)
    
    def export_to_csv(self, properties: List[Dict], filename: str):
        """Export property data to CSV file."""
        df = pd.DataFrame(properties)
        df.to_csv(filename, index=False)
        print(f"Data exported to CSV: {filename}")