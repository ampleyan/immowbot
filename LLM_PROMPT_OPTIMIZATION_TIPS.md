# LLM Prompt Optimization Tips

## Overview
This document provides guidance on how to further optimize the LLM analysis prompts for better property decision-making.

## Current Prompt Structure

The LLM receives:
1. **Property Context** - Type, location, price, surface, EPC score
2. **Market Context** - Average prices for comparison
3. **Description** - Full property description (Dutch/English)
4. **Decision Requirements** - What insights to provide

## Optimization Strategies

### 1. Add Buyer Profile Context

**Current:** Generic analysis for all properties
**Improvement:** Customize analysis based on buyer needs

```python
# In config.py, add buyer profiles:
BUYER_PROFILES = {
    'investor': {
        'priorities': ['rental_yield', 'capital_growth', 'low_maintenance'],
        'concerns': ['vacancy_risk', 'management_complexity']
    },
    'family': {
        'priorities': ['schools', 'safety', 'outdoor_space', 'parking'],
        'concerns': ['noise', 'busy_roads', 'construction']
    },
    'first_time': {
        'priorities': ['move_in_ready', 'manageable_costs', 'growth_potential'],
        'concerns': ['hidden_costs', 'major_repairs', 'difficult_resale']
    }
}
```

**Usage:**
```bash
python main.py --buyer-profile investor --max-price 230000
```

### 2. Location-Specific Intelligence

**Enhancement:** Add known location data to prompt

```python
# Example location database
LOCATION_INTELLIGENCE = {
    '2060': {
        'name': 'Antwerp North',
        'avg_price_m2': 2450,
        'growth_rate': '3.2% annually',
        'amenities': ['Metro line 2', 'Park Spoor Noord', 'Schools'],
        'concerns': ['Gentrification in progress', 'Some areas noisy']
    }
}
```

**Benefit:** LLM can make more informed location assessments

### 3. Temporal Context

**Add to prompt:**
```
MARKET TIMING:
- Current market: {buyer|seller} market
- Interest rates: {current_rate}%
- Seasonal factor: {spring_premium|winter_discount}
- Days on market: {days} (average: {avg_days})
```

**Helps LLM assess:**
- Negotiation leverage
- Urgency of offer
- Realistic price expectations

### 4. Comparable Properties

**Enhancement:** Include similar properties in prompt

```python
# Find 3 most similar properties by:
# - Same postcode
# - Similar surface area (±15%)
# - Similar bedrooms
# - Similar EPC score

comparable_properties = find_comparables(current_property, all_properties, limit=3)

# Add to prompt:
COMPARABLE PROPERTIES:
1. €225,000 - 85m² - EPC: B - 2 bedrooms (2km away)
2. €235,000 - 90m² - EPC: A - 2 bedrooms (1.5km away)
3. €210,000 - 80m² - EPC: C - 2 bedrooms (3km away)
```

**Result:** More accurate price assessment

### 5. Red Flag Detection Rules

**Add specific Belgian real estate red flags:**

```python
RED_FLAGS_CHECKLIST = [
    'Flood zone (check P-score)',
    'Asbestos (pre-2000 construction)',
    'Soil contamination (former industrial)',
    'Co-ownership issues',
    'Urban planning restrictions',
    'Heritage protection constraints',
    'Noise zone (airports, highways)',
    'No habitability certificate',
    'Energy performance below F',
    'Structural issues mentioned'
]
```

### 6. Investment Calculation Prompts

**Current:** Qualitative assessment
**Improvement:** Guide LLM to calculate

```
INVESTMENT METRICS (calculate if possible):
- Gross rental yield: (annual_rent / price) * 100
  Estimate market rent: €X/month based on location and size
- Price per m²: €{price/surface}
- Comparison to area average: {+/-}X%
- Estimated net yield after charges: X%
```

### 7. Renovation Cost Estimation

**Add cost reference:**

```python
RENOVATION_COST_GUIDE = {
    'kitchen': '€8,000 - €15,000',
    'bathroom': '€5,000 - €10,000',
    'painting': '€20 - €35 per m²',
    'flooring': '€30 - €80 per m²',
    'heating': '€3,000 - €8,000',
    'windows': '€500 - €1,000 per window',
    'roof': '€50 - €100 per m²'
}
```

**Helps LLM:** Provide realistic renovation estimates

### 8. Negotiation Strategy Guidance

**Enhancement:** Teach LLM negotiation tactics

```
NEGOTIATION FACTORS:
- Days on market: {days} → leverage {high|medium|low}
- Price changes: {-X% reduction after Y days}
- Market conditions: {buyer|seller|balanced}
- Property condition: {work required}
- Seller motivation signals: {text analysis}

SUGGESTED STRATEGY:
- Initial offer: €X (based on factors above)
- Maximum price: €Y (your calculated fair value)
- Key negotiation points: [list based on cons]
```

### 9. Multi-Language Enhancement

**Current:** Basic Dutch translation
**Improvement:** Cultural context

```python
BELGIAN_REAL_ESTATE_TERMS = {
    'instapklaar': {
        'en': 'move-in ready',
        'meaning': 'No renovation needed',
        'value_impact': '+5-10%'
    },
    'karaktervol': {
        'en': 'characterful',
        'meaning': 'Often means old features, may need updating',
        'value_impact': 'neutral to -5%'
    }
    # Add more...
}
```

### 10. Confidence Calibration

**Add calibration guidelines:**

```
CONFIDENCE SCORING GUIDE:
- 0.9-1.0: Complete description, clear photos, detailed info
- 0.7-0.8: Good description, some details missing
- 0.5-0.6: Vague description, limited information
- 0.3-0.4: Very brief description, many unknowns
- 0.0-0.2: Incomplete or suspicious listing

Adjust analysis detail based on confidence.
```

## Implementation Priority

### Phase 1 (Quick Wins)
1. ✅ Market context (Already implemented!)
2. Add comparable properties
3. Enhanced red flag checklist
4. Confidence calibration

### Phase 2 (Medium Effort)
5. Investment calculations
6. Renovation cost estimation
7. Location intelligence database
8. Negotiation strategy

### Phase 3 (Advanced)
9. Buyer profile customization
10. Temporal market context
11. Multi-language cultural context

## Testing New Prompts

### A/B Testing Approach

```python
# Create two versions of prompt
prompt_v1 = create_analysis_prompt(description, property_info, market_context)
prompt_v2 = create_enhanced_prompt(description, property_info, market_context,
                                   comparables, location_data)

# Compare results
result_v1 = analyze_with_prompt(prompt_v1)
result_v2 = analyze_with_prompt(prompt_v2)

# Metrics to compare:
# - Accuracy of price assessment
# - Usefulness of recommendations
# - Alignment with expert opinion
# - Processing time
```

### Prompt Length vs Quality

**Finding the Balance:**
- Too short: Missing context → poor decisions
- Too long: Token limits, slower processing, potential confusion
- Optimal: 500-800 tokens for context + requirements

**Current Prompt:** ~600 tokens (good!)

## Example Enhanced Prompt

```
You are a Belgian real estate investment expert helping buyers make decisions.

PROPERTY CONTEXT:
- Type: Apartment
- Location: Antwerp, 2060 (Antwerp North - gentrifying area)
- Price: €225,000 (€2,647/m²)
- Surface: 85m²
- Bedrooms: 2
- EPC Score: B

MARKET CONTEXT:
- Area average: €2,450/m² (this is 8% above)
- Market type: Balanced market
- Days on market: 45 (above 30-day average - seller may negotiate)

COMPARABLE PROPERTIES:
1. €215,000 - 82m² - EPC B - 2060 (sold 2 weeks ago)
2. €235,000 - 90m² - EPC A - 2060 (listed 3 days ago)
3. €220,000 - 85m² - EPC C - 2020 (listed 60 days)

LOCATION INTELLIGENCE:
- Area: Up-and-coming, 3.2% annual growth
- Transport: Metro line 2 (300m), good connections
- Amenities: Park Spoor Noord, schools, supermarkets
- Concerns: Some gentrification tension, construction ongoing

DESCRIPTION:
{property_description}

Analyze this property for an investor buyer profile:
- Primary goal: Rental yield + medium-term capital growth
- Risk tolerance: Medium
- Renovation budget: €10,000-€15,000
- Timeline: Can wait 1-2 months for tenant

Provide comprehensive analysis in JSON format...
[rest of prompt]
```

## Monitoring & Improvement

### Track These Metrics

1. **Analysis Quality**
   - User feedback on recommendations
   - Actual vs predicted prices
   - Properties viewed vs viewing_priority

2. **LLM Performance**
   - Response time per property
   - JSON parse success rate
   - Confidence score distribution

3. **Business Impact**
   - Time saved in property screening
   - Better properties identified
   - Money saved through negotiations

### Continuous Improvement Loop

```
┌─────────────────────────────────────────┐
│ 1. Collect user feedback on LLM advice │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 2. Analyze which recommendations worked │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 3. Update prompt with lessons learned   │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 4. A/B test new vs old prompt           │
└───────────────┬─────────────────────────┘
                │
                └──────────► Repeat
```

## Conclusion

The current implementation provides a solid foundation for LLM-powered property analysis. These optimization strategies can be implemented incrementally based on:

1. **User feedback** - What decisions are hardest?
2. **Data availability** - What context can you collect?
3. **Model capabilities** - What can your LLM handle?
4. **Time constraints** - Balance detail vs speed

**Start with:** Comparable properties + red flags (Phase 1)
**Then add:** Investment calculations + location database (Phase 2)
**Advanced:** Buyer profiles + negotiation AI (Phase 3)

---

**Next Steps:**
1. Test current enhanced prompts with real properties
2. Gather feedback on usefulness of new fields
3. Implement Phase 1 optimizations based on results
4. Monitor metrics and iterate
