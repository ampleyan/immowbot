"""
Property market data analyzer.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import re


class PropertyAnalyzer:
    """Analyzes scraped property data to generate market insights."""
    
    def __init__(self, properties: List[Dict]):
        self.properties = properties
        self.df = self._create_dataframe()
        
    def _create_dataframe(self) -> pd.DataFrame:
        """Convert property list to pandas DataFrame for analysis."""
        df = pd.DataFrame(self.properties)
        
        # Clean and convert data types
        if 'price' in df.columns:
            df['price'] = df['price'].apply(self._clean_price)
        
        if 'surface_area' in df.columns:
            df['surface_area'] = df['surface_area'].apply(self._clean_surface_area)
        
        if 'bedrooms' in df.columns:
            df['bedrooms'] = df['bedrooms'].apply(self._clean_bedrooms)
        
        if 'construction_year' in df.columns:
            df['construction_year'] = df['construction_year'].apply(self._clean_year)
        
        # Add calculated fields
        if 'price' in df.columns and 'surface_area' in df.columns:
            df['price_per_m2'] = df['price'] / df['surface_area']
        
        return df
    
    def _clean_price(self, price_str: str) -> float:
        """Clean and convert price string to numeric value."""
        if not price_str or price_str == 'N/A':
            return np.nan
        
        # Remove currency symbols and extract numeric value
        price_match = re.search(r'[\d,]+', str(price_str))
        if price_match:
            price_clean = price_match.group().replace(',', '')
            try:
                return float(price_clean)
            except ValueError:
                return np.nan
        return np.nan
    
    def _clean_surface_area(self, surface_str: str) -> float:
        """Clean and convert surface area string to numeric value."""
        if not surface_str or surface_str == 'N/A':
            return np.nan
        
        # Extract numeric value
        surface_match = re.search(r'\d+', str(surface_str))
        if surface_match:
            try:
                return float(surface_match.group())
            except ValueError:
                return np.nan
        return np.nan
    
    def _clean_bedrooms(self, bedroom_str: str) -> int:
        """Clean and convert bedroom string to numeric value."""
        if not bedroom_str or bedroom_str == 'N/A':
            return np.nan
        
        # Extract numeric value
        bedroom_match = re.search(r'\d+', str(bedroom_str))
        if bedroom_match:
            try:
                return int(bedroom_match.group())
            except ValueError:
                return np.nan
        return np.nan
    
    def _clean_year(self, year_str: str) -> int:
        """Clean and convert construction year string to numeric value."""
        if not year_str or year_str == 'N/A':
            return np.nan
        
        # Extract 4-digit year
        year_match = re.search(r'\b(19|20)\d{2}\b', str(year_str))
        if year_match:
            try:
                return int(year_match.group())
            except ValueError:
                return np.nan
        return np.nan
    
    def generate_analysis(self) -> Dict[str, Any]:
        """Generate comprehensive market analysis."""
        analysis = {
            'summary': self._generate_summary(),
            'price_analysis': self._analyze_prices(),
            'location_analysis': self._analyze_locations(),
            'postcode_analysis': self._analyze_postcodes(),
            'epc_analysis': self._analyze_epc_scores(),
            'size_analysis': self._analyze_property_sizes(),
            'feature_analysis': self._analyze_property_features(),
            'geographic_analysis': self._analyze_geographic_distribution(),
            'market_segments': self._analyze_market_segments(),
            'recommendations': self._generate_recommendations()
        }
        
        return analysis
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate basic summary statistics."""
        total_properties = len(self.df)
        
        price_stats = {}
        if 'price' in self.df.columns and not self.df['price'].isna().all():
            price_stats = {
                'mean_price': self.df['price'].mean(),
                'median_price': self.df['price'].median(),
                'min_price': self.df['price'].min(),
                'max_price': self.df['price'].max(),
                'std_price': self.df['price'].std()
            }
        
        return {
            'total_properties': total_properties,
            'price_statistics': price_stats,
            'data_completeness': self._calculate_data_completeness()
        }
    
    def _calculate_data_completeness(self) -> Dict[str, float]:
        """Calculate completeness percentage for each field."""
        completeness = {}
        for column in self.df.columns:
            non_null_count = self.df[column].notna().sum()
            completeness[column] = (non_null_count / len(self.df)) * 100
        return completeness
    
    def _analyze_prices(self) -> Dict[str, Any]:
        """Analyze price distributions and trends."""
        if 'price' not in self.df.columns or self.df['price'].isna().all():
            return {"error": "No price data available"}
        
        prices = self.df['price'].dropna()
        
        # Price ranges
        price_ranges = {
            'under_150k': (prices < 150000).sum(),
            '150k_200k': ((prices >= 150000) & (prices < 200000)).sum(),
            '200k_250k': ((prices >= 200000) & (prices < 250000)).sum(),
            '250k_300k': ((prices >= 250000) & (prices < 300000)).sum(),
            'over_300k': (prices >= 300000).sum()
        }
        
        analysis = {
            'price_ranges': price_ranges,
            'quartiles': {
                'q1': prices.quantile(0.25),
                'q2': prices.quantile(0.5),
                'q3': prices.quantile(0.75)
            }
        }
        
        # Price per m2 analysis if surface area is available
        if 'price_per_m2' in self.df.columns:
            price_per_m2 = self.df['price_per_m2'].dropna()
            if len(price_per_m2) > 0:
                analysis['price_per_m2'] = {
                    'mean': price_per_m2.mean(),
                    'median': price_per_m2.median(),
                    'std': price_per_m2.std()
                }
        
        return analysis
    
    def _analyze_locations(self) -> Dict[str, Any]:
        """Analyze property distribution by location."""
        if 'location' not in self.df.columns:
            return {"error": "No location data available"}
        
        location_counts = self.df['location'].value_counts()
        
        # Average prices by location (if price data is available)
        location_prices = {}
        if 'price' in self.df.columns:
            location_prices = self.df.groupby('location')['price'].agg(['mean', 'median', 'count']).to_dict('index')
        
        return {
            'location_distribution': location_counts.to_dict(),
            'location_price_analysis': location_prices
        }
    
    def _analyze_postcodes(self) -> Dict[str, Any]:
        """Analyze property distribution by postcode."""
        if 'postcode' not in self.df.columns:
            return {"error": "No postcode data available"}
        
        postcode_counts = self.df['postcode'].value_counts()
        
        # Average prices by postcode (if price data is available)
        postcode_prices = {}
        if 'price' in self.df.columns:
            postcode_prices = self.df.groupby('postcode')['price'].agg(['mean', 'median', 'count']).to_dict('index')
        
        return {
            'postcode_distribution': postcode_counts.to_dict(),
            'postcode_price_analysis': postcode_prices
        }
    
    def _analyze_epc_scores(self) -> Dict[str, Any]:
        """Analyze EPC energy efficiency scores."""
        if 'epc_score' not in self.df.columns:
            return {"error": "No EPC data available"}
        
        epc_counts = self.df['epc_score'].value_counts()
        
        # Average prices by EPC score
        epc_prices = {}
        if 'price' in self.df.columns:
            epc_prices = self.df.groupby('epc_score')['price'].agg(['mean', 'median', 'count']).to_dict('index')
        
        return {
            'epc_distribution': epc_counts.to_dict(),
            'epc_price_analysis': epc_prices
        }
    
    def _analyze_property_sizes(self) -> Dict[str, Any]:
        """Analyze property sizes and bedroom distribution."""
        analysis = {}
        
        # Surface area analysis
        if 'surface_area' in self.df.columns:
            surface_areas = self.df['surface_area'].dropna()
            if len(surface_areas) > 0:
                analysis['surface_area'] = {
                    'mean': surface_areas.mean(),
                    'median': surface_areas.median(),
                    'min': surface_areas.min(),
                    'max': surface_areas.max(),
                    'std': surface_areas.std()
                }
        
        # Bedroom analysis
        if 'bedrooms' in self.df.columns:
            bedroom_counts = self.df['bedrooms'].value_counts()
            analysis['bedroom_distribution'] = bedroom_counts.to_dict()
        
        return analysis
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if 'price' in self.df.columns and not self.df['price'].isna().all():
            median_price = self.df['price'].median()
            recommendations.append(f"Median property price: €{median_price:,.0f}")
        
        if 'epc_score' in self.df.columns:
            epc_counts = self.df['epc_score'].value_counts()
            if len(epc_counts) > 0:
                most_common_epc = epc_counts.index[0]
                recommendations.append(f"Most common EPC score: {most_common_epc}")
        
        if 'location' in self.df.columns and 'price' in self.df.columns:
            location_prices = self.df.groupby('location')['price'].median().sort_values()
            if len(location_prices) > 0:
                cheapest_area = location_prices.index[0]
                recommendations.append(f"Most affordable area: {cheapest_area} (median: €{location_prices.iloc[0]:,.0f})")
        
        if 'price_per_m2' in self.df.columns:
            median_price_per_m2 = self.df['price_per_m2'].median()
            if not pd.isna(median_price_per_m2):
                recommendations.append(f"Median price per m²: €{median_price_per_m2:.0f}/m²")
        
        return recommendations
    
    def _analyze_property_features(self) -> Dict[str, Any]:
        """Analyze property features and amenities."""
        analysis = {}
        
        # Building state analysis
        if 'building_state' in self.df.columns:
            building_states = self.df['building_state'].value_counts()
            analysis['building_states'] = building_states.to_dict()
            
            # Price by building state
            if 'price' in self.df.columns:
                state_prices = self.df.groupby('building_state')['price'].agg(['mean', 'median', 'count']).to_dict('index')
                analysis['building_state_prices'] = state_prices
        
        # Kitchen type analysis
        if 'kitchen_type' in self.df.columns:
            kitchen_types = self.df['kitchen_type'].value_counts()
            analysis['kitchen_types'] = kitchen_types.to_dict()
        
        # Amenities analysis
        amenities = {}
        for amenity in ['outdoor_terrace', 'parking']:
            if amenity in self.df.columns:
                amenity_counts = self.df[amenity].value_counts()
                amenities[amenity] = amenity_counts.to_dict()
                
                # Price impact of amenities
                if 'price' in self.df.columns:
                    amenity_prices = self.df.groupby(amenity)['price'].agg(['mean', 'median', 'count']).to_dict('index')
                    amenities[f'{amenity}_price_impact'] = amenity_prices
        
        analysis['amenities'] = amenities
        
        # Energy type analysis
        if 'energy_type' in self.df.columns:
            energy_types = self.df['energy_type'].value_counts()
            analysis['energy_types'] = energy_types.to_dict()
            
            if 'price' in self.df.columns:
                energy_prices = self.df.groupby('energy_type')['price'].agg(['mean', 'median', 'count']).to_dict('index')
                analysis['energy_type_prices'] = energy_prices
        
        return analysis
    
    def _analyze_geographic_distribution(self) -> Dict[str, Any]:
        """Analyze geographic distribution of properties."""
        analysis = {}
        
        # Province analysis
        if 'province' in self.df.columns:
            province_counts = self.df['province'].value_counts()
            analysis['province_distribution'] = province_counts.to_dict()
            
            if 'price' in self.df.columns:
                province_prices = self.df.groupby('province')['price'].agg(['mean', 'median', 'count']).to_dict('index')
                analysis['province_prices'] = province_prices
        
        # City analysis
        if 'city' in self.df.columns:
            city_counts = self.df['city'].value_counts()
            analysis['city_distribution'] = city_counts.head(10).to_dict()  # Top 10 cities
            
            if 'price' in self.df.columns:
                city_prices = self.df.groupby('city')['price'].agg(['mean', 'median', 'count'])
                # Get top 10 most expensive and cheapest cities
                analysis['most_expensive_cities'] = city_prices.sort_values('median', ascending=False).head(5).to_dict('index')
                analysis['most_affordable_cities'] = city_prices.sort_values('median', ascending=True).head(5).to_dict('index')
        
        # Coordinate-based analysis (if coordinates are available)
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            coords_df = self.df[['latitude', 'longitude', 'price']].dropna()
            if len(coords_df) > 0:
                analysis['coordinate_bounds'] = {
                    'north': coords_df['latitude'].max(),
                    'south': coords_df['latitude'].min(),
                    'east': coords_df['longitude'].max(),
                    'west': coords_df['longitude'].min(),
                    'center_lat': coords_df['latitude'].mean(),
                    'center_lng': coords_df['longitude'].mean()
                }
        
        return analysis
    
    def _analyze_market_segments(self) -> Dict[str, Any]:
        """Analyze different market segments."""
        analysis = {}
        
        # Price segments
        if 'price' in self.df.columns:
            prices = self.df['price'].dropna()
            if len(prices) > 0:
                # Define price segments
                q1, q2, q3 = prices.quantile([0.25, 0.5, 0.75])
                
                def categorize_price(price):
                    if price <= q1:
                        return 'Budget (Bottom 25%)'
                    elif price <= q2:
                        return 'Mid-Low (25-50%)'
                    elif price <= q3:
                        return 'Mid-High (50-75%)'
                    else:
                        return 'Luxury (Top 25%)'
                
                self.df['price_segment'] = self.df['price'].apply(categorize_price)
                price_segments = self.df['price_segment'].value_counts()
                analysis['price_segments'] = price_segments.to_dict()
                
                # Characteristics by price segment
                if 'surface_area' in self.df.columns:
                    segment_surface = self.df.groupby('price_segment')['surface_area'].agg(['mean', 'median']).to_dict('index')
                    analysis['segment_surface_area'] = segment_surface
                
                if 'bedrooms' in self.df.columns:
                    segment_bedrooms = self.df.groupby('price_segment')['bedrooms'].agg(['mean', 'median']).to_dict('index')
                    analysis['segment_bedrooms'] = segment_bedrooms
        
        # Property type segments
        if 'property_type' in self.df.columns and 'price' in self.df.columns:
            type_analysis = self.df.groupby('property_type').agg({
                'price': ['mean', 'median', 'count'],
                'surface_area': ['mean', 'median'] if 'surface_area' in self.df.columns else None,
                'bedrooms': ['mean', 'median'] if 'bedrooms' in self.df.columns else None
            }).to_dict('index')
            analysis['property_type_analysis'] = type_analysis
        
        return analysis