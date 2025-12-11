"""
LLM-based property description analyzer using Ollama.
"""
import requests
import json
import time
from typing import Dict, List, Optional, Any
import logging


class OllamaPropertyAnalyzer:
    """Analyzes property descriptions using local Ollama LLM to extract insights."""
    
    # Common Dutch real estate terms for better translation context
    DUTCH_TERMS_CONTEXT = {
        'woning': 'property/home',
        'tuin': 'garden',
        'zolder': 'attic', 
        'kelder': 'basement/cellar',
        'badkamer': 'bathroom',
        'slaapkamer': 'bedroom',
        'keuken': 'kitchen',
        'woonkamer': 'living room',
        'terras': 'terrace',
        'garage': 'garage',
        'parket': 'hardwood flooring',
        'tegels': 'tiles',
        'renovatie': 'renovation',
        'instapklaar': 'move-in ready',
        'opfrissing': 'refresh/light renovation',
        'centrale verwarming': 'central heating',
        'dubbele beglazing': 'double glazing',
        'rustige buurt': 'quiet neighborhood',
        'nabij': 'near/close to',
        'openbaar vervoer': 'public transport'
    }
    
    def __init__(self, ollama_host: str = "http://localhost:11434", model_name: str = "mistral:7b-instruct", speed_mode: bool = False):
        self.ollama_host = ollama_host.rstrip('/')
        self.model_name = model_name
        self.speed_mode = speed_mode
        self.session = requests.Session()
        
        # Check if Ollama is running and model is available
        self.is_available = self._check_ollama_availability()
        
    def _check_ollama_availability(self) -> bool:
        """Check if Ollama is running and the specified model is available."""
        try:
            # Check if Ollama is running
            response = self.session.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code != 200:
                print(f"❌ Ollama not running at {self.ollama_host}")
                return False
            
            # Check if model is available
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            if self.model_name not in model_names:
                print(f"❌ Model '{self.model_name}' not found in Ollama")
                print(f"Available models: {', '.join(model_names)}")
                return False
            
            print(f"✅ Ollama detected with model '{self.model_name}'")
            return True
            
        except Exception as e:
            print(f"❌ Error connecting to Ollama: {e}")
            return False
    
    def _create_analysis_prompt(self, description: str, property_info: Dict, market_context: Dict = None) -> str:
        """Create a structured prompt for property description analysis with decision-support focus."""
        price = property_info.get('price', 'Unknown')
        location = property_info.get('location', 'Unknown')
        surface_area = property_info.get('surface_area', 'Unknown')
        epc_score = property_info.get('epc_score', 'Unknown')
        property_type = property_info.get('property_type', 'Unknown')
        bedrooms = property_info.get('bedrooms', 'Unknown')

        price_str = f"€{price:,}" if price != 'Unknown' and isinstance(price, (int, float)) else str(price)
        surface_str = f"{surface_area}m²" if surface_area != 'Unknown' else str(surface_area)

        market_info = ""
        if market_context:
            avg_price = market_context.get('avg_price_per_m2', 'Unknown')
            avg_total = market_context.get('avg_total_price', 'Unknown')
            market_info = f'''
        MARKET CONTEXT:
        - Average price/m² in area: €{avg_price:.0f}/m² (if available)
        - Average total price: €{avg_total:,.0f} (if available)
        - This property price/m²: €{price/surface_area:.0f}/m² (if calculable)'''

        prompt = f'''You are a Belgian real estate investment expert helping buyers make informed decisions.

        PROPERTY CONTEXT:
        - Type: {property_type}
        - Location: {location}
        - Price: {price_str}
        - Surface: {surface_str}
        - Bedrooms: {bedrooms}
        - EPC Score: {epc_score}{market_info}

        DESCRIPTION TO ANALYZE:
        {description}

        Analyze this property and provide comprehensive decision-support insights in JSON format.
        Your analysis should help the buyer decide if they should view/buy this property.

        TRANSLATION REFERENCE:
        - woning = property/home, badkamer = bathroom, slaapkamer = bedroom
        - keuken = kitchen, centrale verwarming = central heating
        - dubbele beglazing = double glazing, instapklaar = move-in ready
        - nieuwbouw = new construction, te renoveren = needs renovation
        - huurder/tenant/verhuurd = rented/has tenant, huurcontract = rental contract

        IMPORTANT: Check if property has current tenants. If tenants are mentioned:
        - Add "Current tenant in place" to red_flags
        - Set viewing_priority to "low" or "skip" (unless investor seeking rental income)
        - Note tenant situation in main_concerns
        - Mention in summary that property is currently tenanted

        REQUIRED JSON OUTPUT FORMAT:
        {{
            "pros": ["list of positive aspects"],
            "cons": ["list of negative aspects or concerns"],
            "key_features": ["standout features worth noting"],
            "condition_assessment": {{
                "overall": "excellent|good|fair|needs_work|poor",
                "details": "explanation of condition"
            }},
            "value_indicators": {{
                "overpriced_signals": ["reasons property might be overpriced"],
                "good_value_signals": ["reasons property might be good value"],
                "price_justification": "detailed price assessment",
                "estimated_fair_price_range": "€XXX,XXX - €XXX,XXX"
            }},
            "investment_analysis": {{
                "rental_potential": "excellent|good|fair|poor",
                "resale_potential": "excellent|good|fair|poor",
                "capital_growth_outlook": "high|medium|low",
                "renovation_required": "none|minor|moderate|major",
                "estimated_renovation_cost": "€X,XXX - €XX,XXX or none",
                "time_to_market": "move-in ready|1-3 months|3-6 months|6+ months"
            }},
            "location_quality": {{
                "neighborhood_rating": "excellent|good|average|poor",
                "transport_accessibility": "excellent|good|average|poor",
                "amenities_nearby": ["list of mentioned nearby amenities"],
                "location_concerns": ["any location-related issues"]
            }},
            "decision_support": {{
                "viewing_priority": "must_view|high|medium|low|skip",
                "deal_quality_score": 0.0-10.0,
                "investment_score": 0.0-10.0,
                "recommended_action": "view_immediately|schedule_viewing|negotiate_first|pass",
                "negotiation_potential": "€X,XXX potential reduction|limited|none",
                "main_selling_points": ["top 3 reasons to buy"],
                "main_concerns": ["top 3 reasons to hesitate"]
            }},
            "red_flags": ["critical issues or deal-breakers"],
            "summary": "2-3 sentence executive summary for decision-making",
            "confidence_score": 0.0-1.0
        }}'''

        return prompt

    def _query_ollama(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Send a query to Ollama and return the response."""
        if not self.is_available:
            return None

        # Use chat endpoint instead
        url = f"{self.ollama_host}/api/chat"

        # Configure options
        options = {
            "temperature": 0.1,
            "top_p": 0.8,
            "num_predict": 800 if self.speed_mode else 1200,
            "repeat_penalty": 1.6,
            "num_ctx": 1024 if self.speed_mode else 2048,
        }

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": options,
            # Add JSON format enforcement
            "format": {
                "type": "object",
                "properties": {
                    "pros": {"type": "array", "items": {"type": "string"}},
                    "cons": {"type": "array", "items": {"type": "string"}},
                    "key_features": {"type": "array", "items": {"type": "string"}},
                    "condition_assessment": {
                        "type": "object",
                        "properties": {
                            "overall": {"type": "string"},
                            "details": {"type": "string"}
                        },
                        "required": ["overall", "details"]
                    },
                    "value_indicators": {
                        "type": "object",
                        "properties": {
                            "overpriced_signals": {"type": "array", "items": {"type": "string"}},
                            "good_value_signals": {"type": "array", "items": {"type": "string"}},
                            "price_justification": {"type": "string"},
                            "estimated_fair_price_range": {"type": "string"}
                        },
                        "required": ["overpriced_signals", "good_value_signals", "price_justification"]
                    },
                    "investment_analysis": {
                        "type": "object",
                        "properties": {
                            "rental_potential": {"type": "string"},
                            "resale_potential": {"type": "string"},
                            "capital_growth_outlook": {"type": "string"},
                            "renovation_required": {"type": "string"},
                            "estimated_renovation_cost": {"type": "string"},
                            "time_to_market": {"type": "string"}
                        }
                    },
                    "location_quality": {
                        "type": "object",
                        "properties": {
                            "neighborhood_rating": {"type": "string"},
                            "transport_accessibility": {"type": "string"},
                            "amenities_nearby": {"type": "array", "items": {"type": "string"}},
                            "location_concerns": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "decision_support": {
                        "type": "object",
                        "properties": {
                            "viewing_priority": {"type": "string"},
                            "deal_quality_score": {"type": "number"},
                            "investment_score": {"type": "number"},
                            "recommended_action": {"type": "string"},
                            "negotiation_potential": {"type": "string"},
                            "main_selling_points": {"type": "array", "items": {"type": "string"}},
                            "main_concerns": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "red_flags": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string"},
                    "confidence_score": {"type": "number"}
                },
                "required": ["pros", "cons", "key_features", "condition_assessment",
                             "value_indicators", "red_flags", "summary", "confidence_score"]
            }
        }

        for attempt in range(max_retries):
            try:
                # response = self.session.post(
                #     f"{self.ollama_host}/api/generate",
                #     json=payload,
                #     timeout=120  # E
                # )
                response = self.session.post(url, json=payload, timeout=120)

                if response.status_code == 200:
                    result = response.json()

                    raw_response = result.get('message', {}).get('content', '').strip()

                    # With format enforcement, should already be valid JSON
                    try:
                        resp = json.loads(raw_response)  # Validate JSON
                        return resp
                    except json.JSONDecodeError:
                        print(f"⚠️  Attempt {attempt + 1}: Invalid JSON despite format enforcement")
                        continue
                else:
                    print(f"Ollama API error: HTTP {response.status_code}")

            except Exception as e:
                if "timeout" in str(e).lower():
                    print(f"⏱️  Attempt {attempt + 1} timed out after 120s - model may be slow")
                else:
                    print(f"❌ Attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    wait_time = 5 if "timeout" in str(e).lower() else 2
                    print(f"   Retrying in {wait_time}s...")
                    time.sleep(wait_time)

        return None
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean up common JSON formatting issues from LLM responses."""
        import re
        
        # Remove markdown code blocks
        json_str = re.sub(r'```json5?', '', json_str)
        json_str = re.sub(r'```', '', json_str)
        
        # Remove all types of comments
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'#.*$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # Fix broken property names and values
        json_str = re.sub(r'"pro":', '"pros":', json_str)
        json_str = re.sub(r'"con":', '"cons":', json_str)
        
        # Remove comments in array/object items
        json_str = re.sub(r'],\s*[#/].*', ']', json_str)
        json_str = re.sub(r'",\s*[#/].*', '"', json_str)
        json_str = re.sub(r'},\s*[#/].*', '}', json_str)
        
        # Fix invalid JSON5 syntax and trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Fix malformed confidence score
        json_str = re.sub(r'"confidence_score":\s*0(\d)', r'"confidence_score":0.\1', json_str)
        
        # Remove any text after the closing brace
        brace_count = 0
        end_pos = 0
        for i, char in enumerate(json_str):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > 0:
            json_str = json_str[:end_pos]
        
        return json_str.strip()
    
    def _validate_and_fix_json_response(self, response: str) -> Optional[str]:
        """Validate and fix JSON response immediately when received from LLM."""
        if not response:
            return None
        
        print(f"🔍 Raw LLM response: {response[:200]}...")
        
        # Remove markdown code blocks if present
        if "```json" in response:
            response = response.replace("```json", "").replace("```", "")
        
        # Check for immediate red flags
        bad_patterns = ["document:", "you are an ai", "the property is located on 12345", 
                       "$60 million", "price_in dutch", "eighty's ago"]
        response_lower = response.lower()
        for pattern in bad_patterns:
            if pattern in response_lower:
                print(f"❌ Rejected: contains bad pattern '{pattern}'")
                return None
        
        try:
            # Try to extract and validate JSON
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                print("❌ Rejected: no complete JSON found")
                return None
            
            json_str = response[start_idx:end_idx + 1]
            json_str = self._clean_json_string(json_str)
            
            print(f"🔧 Cleaned JSON: {json_str[:150]}...")
            
            # Test parse the JSON
            parsed = json.loads(json_str)
            
            # Validate required structure
            required_fields = ['pros', 'cons', 'key_features', 'condition_assessment', 'summary']
            if not all(field in parsed for field in required_fields):
                missing = [f for f in required_fields if f not in parsed]
                print(f"❌ Rejected: missing fields {missing}")
                return None
            
            # Ensure condition_assessment is properly structured
            if not isinstance(parsed.get('condition_assessment'), dict):
                print("❌ Rejected: condition_assessment not a dict")
                return None
            
            if 'overall' not in parsed['condition_assessment']:
                print("❌ Rejected: condition_assessment missing 'overall'")
                return None
            
            print("✅ JSON validated successfully")
            # Return the cleaned JSON string (not the original response)
            return json_str
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"❌ Rejected: JSON error {e}")
            return None
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse the pre-validated LLM response."""
        if not response:
            return self._get_error_response("No response from LLM")
        
        try:
            # Response should already be validated and cleaned JSON string
            if isinstance(response, dict):
                return response
            else:
                parsed = json.loads(response)
                return parsed
                
        except json.JSONDecodeError as e:
            print(f"Unexpected JSON parsing error in pre-validated response: {e}")
            return self._create_basic_analysis(response)
    
    def _create_basic_analysis(self, text: str) -> Dict[str, Any]:
        """Create a basic analysis structure when JSON parsing fails."""
        return {
            "pros": [text[:200] + "..." if len(text) > 200 else text],
            "cons": ["Analysis parsing incomplete"],
            "key_features": ["See raw analysis"],
            "condition_assessment": {
                "overall": "unknown",
                "details": "Could not parse detailed assessment"
            },
            "value_indicators": {
                "overpriced_signals": [],
                "good_value_signals": [],
                "price_justification": "Analysis incomplete"
            },
            "investment_potential": {
                "rental_suitability": "unknown",
                "resale_potential": "unknown", 
                "renovation_opportunity": "Analysis incomplete"
            },
            "red_flags": ["Analysis parsing failed"],
            "summary": text[:300] + "..." if len(text) > 300 else text,
            "confidence_score": 0.1,
            "raw_analysis": text
        }
    
    def _get_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Return error response structure."""
        return {
            "pros": [],
            "cons": [],
            "key_features": [],
            "condition_assessment": {
                "overall": "unknown",
                "details": error_msg
            },
            "value_indicators": {
                "overpriced_signals": [],
                "good_value_signals": [],
                "price_justification": "Analysis failed",
                "estimated_fair_price_range": "Unknown"
            },
            "investment_analysis": {
                "rental_potential": "unknown",
                "resale_potential": "unknown",
                "capital_growth_outlook": "unknown",
                "renovation_required": "unknown",
                "estimated_renovation_cost": "Unknown",
                "time_to_market": "unknown"
            },
            "location_quality": {
                "neighborhood_rating": "unknown",
                "transport_accessibility": "unknown",
                "amenities_nearby": [],
                "location_concerns": []
            },
            "decision_support": {
                "viewing_priority": "unknown",
                "deal_quality_score": 0.0,
                "investment_score": 0.0,
                "recommended_action": "analysis_failed",
                "negotiation_potential": "Unknown",
                "main_selling_points": [],
                "main_concerns": [error_msg]
            },
            "red_flags": [error_msg],
            "summary": f"Analysis failed: {error_msg}",
            "confidence_score": 0.0,
            "error": error_msg
        }
    
    def analyze_property_description(self, description: str, property_info: Dict, market_context: Dict = None) -> Dict[str, Any]:
        """Analyze a single property description and return structured insights with market context."""
        if not description or not description.strip():
            return self._get_error_response("No description provided")

        if not self.is_available:
            return self._get_error_response("Ollama not available")

        print(f"🤖 Analyzing property description with {self.model_name}...")

        prompt = self._create_analysis_prompt(description, property_info, market_context)

        response = self._query_ollama(prompt)

        if not response:
            return self._get_error_response("LLM query failed")

        analysis = self._parse_llm_response(response)

        analysis['analyzed_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
        analysis['model_used'] = self.model_name
        analysis['description_length'] = len(description)

        return analysis
    
    def _calculate_market_context(self, properties: List[Dict]) -> Dict[str, Any]:
        """Calculate market context from all properties for comparison."""
        valid_prices = []
        valid_price_per_m2 = []

        for prop in properties:
            price = prop.get('price')
            surface = prop.get('surface_area')

            if price and isinstance(price, (int, float)) and price > 0:
                valid_prices.append(price)

                if surface and isinstance(surface, (int, float)) and surface > 0:
                    valid_price_per_m2.append(price / surface)

        market_context = {}
        if valid_prices:
            market_context['avg_total_price'] = sum(valid_prices) / len(valid_prices)
            market_context['median_total_price'] = sorted(valid_prices)[len(valid_prices) // 2]

        if valid_price_per_m2:
            market_context['avg_price_per_m2'] = sum(valid_price_per_m2) / len(valid_price_per_m2)
            market_context['median_price_per_m2'] = sorted(valid_price_per_m2)[len(valid_price_per_m2) // 2]

        return market_context

    def analyze_multiple_properties(self, properties: List[Dict]) -> List[Dict]:
        """Analyze descriptions for multiple properties with market context."""
        if not self.is_available:
            print("❌ Ollama not available - skipping description analysis")
            return properties

        total_properties = len(properties)
        analyzed_properties = []
        successful_analyses = 0
        failed_analyses = 0

        market_context = self._calculate_market_context(properties)
        if market_context:
            print(f"📊 Market context calculated:")
            if 'avg_price_per_m2' in market_context:
                print(f"   Average price/m²: €{market_context['avg_price_per_m2']:.0f}")
            if 'avg_total_price' in market_context:
                print(f"   Average total price: €{market_context['avg_total_price']:,.0f}")

        print(f"🤖 Starting LLM analysis for {total_properties} properties...")
        print(f"⏱️  Using 120s timeout per property - this may take a while...")

        for i, property_data in enumerate(properties, 1):
            print(f"   [{i}/{total_properties}] {property_data.get('location', 'Unknown')}")

            description = property_data.get('description', '')

            if description and description.strip():
                analysis = self.analyze_property_description(description, property_data, market_context)

                if analysis.get('error'):
                    print(f"   ❌ Analysis failed: {analysis['error']}")
                    failed_analyses += 1
                    property_data['has_llm_analysis'] = False
                else:
                    successful_analyses += 1
                    property_data['has_llm_analysis'] = True

                property_data['llm_analysis'] = analysis

                property_data['llm_summary'] = analysis.get('summary', '')
                property_data['llm_pros'] = '; '.join(analysis.get('pros', []))
                property_data['llm_cons'] = '; '.join(analysis.get('cons', []))
                property_data['llm_condition'] = analysis.get('condition_assessment', {}).get('overall', 'unknown')
                property_data['llm_confidence'] = analysis.get('confidence_score', 0.0)

                decision_support = analysis.get('decision_support', {})
                property_data['llm_viewing_priority'] = decision_support.get('viewing_priority', 'unknown')
                property_data['llm_deal_score'] = decision_support.get('deal_quality_score', 0.0)
                property_data['llm_investment_score'] = decision_support.get('investment_score', 0.0)
                property_data['llm_recommended_action'] = decision_support.get('recommended_action', 'unknown')

                time.sleep(0.2)
            else:
                print(f"   ⏭️  No description - skipping")
                property_data['has_llm_analysis'] = False
                property_data['llm_analysis'] = self._get_error_response("No description available")

            analyzed_properties.append(property_data)

        print(f"\n🎉 LLM analysis completed:")
        print(f"   ✅ Successful: {successful_analyses}/{total_properties}")
        print(f"   ❌ Failed: {failed_analyses}/{total_properties}")
        if failed_analyses > 0:
            print(f"   💡 Consider using a faster model like 'llama3.1:7b' or increasing system resources")

        return analyzed_properties
    
    def get_analysis_summary(self, properties: List[Dict]) -> Dict[str, Any]:
        """Generate a summary of LLM analysis results across all properties."""
        analyzed = [p for p in properties if p.get('has_llm_analysis')]
        total_analyzed = len(analyzed)
        
        if total_analyzed == 0:
            return {"error": "No properties with LLM analysis found"}
        
        # Aggregate insights
        all_conditions = [p.get('llm_condition', 'unknown') for p in analyzed]
        condition_counts = {}
        for condition in all_conditions:
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
        
        # Average confidence
        confidences = [p.get('llm_confidence', 0) for p in analyzed if p.get('llm_confidence')]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Most common pros and cons (simplified)
        all_pros = []
        all_cons = []
        for prop in analyzed:
            if prop.get('llm_analysis'):
                all_pros.extend(prop['llm_analysis'].get('pros', []))
                all_cons.extend(prop['llm_analysis'].get('cons', []))
        
        return {
            "total_properties_analyzed": total_analyzed,
            "average_confidence": avg_confidence,
            "condition_distribution": condition_counts,
            "total_pros_identified": len(all_pros),
            "total_cons_identified": len(all_cons),
            "model_used": self.model_name
        }