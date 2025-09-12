#!/usr/bin/env python3
"""
Debug script to test scraping and LLM analysis independently.
"""
import json
from src.scraper import ImmowebScraper
from src.llm_analyzer import OllamaPropertyAnalyzer

def test_single_property_scraping():
    """Test scraping a single property URL."""
    print("🔍 Testing single property scraping...")
    
    # Test URL (you can change this to any Immoweb property URL)
    test_url = "https://www.immoweb.be/en/classified/apartment/for-sale/borgerhout/2140/20842667"
    
    scraper = ImmowebScraper()
    
    # Try to scrape just this one property
    properties = scraper.scrape_from_url(test_url, max_pages=1)
    
    if properties:
        prop = properties[0]
        print(f"✅ Successfully scraped property:")
        print(f"   Name: {prop.get('name', 'N/A')}")
        print(f"   Price: €{prop.get('price', 0):,}")
        print(f"   Location: {prop.get('location', 'N/A')}")
        print(f"   Surface: {prop.get('surface_area', 'N/A')} m²")
        print(f"   EPC: {prop.get('epc_score', 'N/A')}")
        print(f"   Property Type: {prop.get('property_type', 'N/A')}")
        print(f"   Bedrooms: {prop.get('bedrooms', 'N/A')}")
        print(f"   Construction Year: {prop.get('construction_year', 'N/A')}")
        print(f"   Description length: {len(prop.get('description', ''))}")
        if prop.get('description'):
            print(f"   Description preview: {prop.get('description', '')[:150]}...")
        
        # Save for LLM testing
        with open('debug_property.json', 'w', encoding='utf-8') as f:
            json.dump([prop], f, indent=2, ensure_ascii=False)
        print(f"   Saved to debug_property.json")
        
        return prop
    else:
        print("❌ Failed to scrape property")
        return None

def test_llm_analysis():
    """Test LLM analysis with a sample property."""
    print("\n🤖 Testing LLM analysis...")
    
    # Try to load saved property
    try:
        with open('debug_property.json', 'r', encoding='utf-8') as f:
            properties = json.load(f)
        prop = properties[0]
        print(f"✅ Loaded property: {prop.get('name', 'Unknown')}")
    except FileNotFoundError:
        print("❌ No debug_property.json found. Run test_single_property_scraping() first.")
        return
    
    # Test LLM analyzer
    analyzer = OllamaPropertyAnalyzer(speed_mode=True)  # Use speed mode for testing
    
    if not analyzer.is_available:
        print("❌ Ollama not available")
        return
    
    description = prop.get('description', '')
    if not description:
        print("⚠️ No description found in property data")
        return
    
    print(f"📝 Description length: {len(description)} characters")
    print(f"📝 Description preview: {description[:200]}...")
    
    # Analyze the description
    print("🔍 Starting LLM analysis...")
    analysis = analyzer.analyze_property_description(description, prop)
    
    if analysis.get('error'):
        print(f"❌ LLM analysis failed: {analysis['error']}")
    else:
        print(f"✅ LLM analysis completed!")
        print(f"   Confidence: {analysis.get('confidence_score', 0):.2f}")
        print(f"   Condition: {analysis.get('condition_assessment', {}).get('overall', 'unknown')}")
        print(f"   Pros: {len(analysis.get('pros', []))} identified")
        print(f"   Cons: {len(analysis.get('cons', []))} identified")
        
        # Show first few pros/cons
        if analysis.get('pros'):
            print(f"   First pro: {analysis['pros'][0]}")
        if analysis.get('cons'):
            print(f"   First con: {analysis['cons'][0]}")
        
        print(f"   Summary: {analysis.get('summary', 'N/A')}")

def main():
    """Run debug tests."""
    print("🐛 Immowbot Debug Script")
    print("=" * 50)
    
    # Test scraping
    prop = test_single_property_scraping()
    
    if prop:
        # Test LLM analysis
        test_llm_analysis()
    
    print("\n" + "=" * 50)
    print("🔚 Debug complete")

if __name__ == "__main__":
    main()