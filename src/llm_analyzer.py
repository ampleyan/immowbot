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
    
    def __init__(self, ollama_host: str = "http://localhost:11434", model_name: str = "mistral:7b", speed_mode: bool = False):
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
    
    def _create_analysis_prompt(self, description: str, property_info: Dict) -> str:
        """Create a structured prompt for property description analysis."""
        
        # Extract key property details for context
        price = property_info.get('price', 'Unknown')
        location = property_info.get('location', 'Unknown')
        surface_area = property_info.get('surface_area', 'Unknown')
        epc_score = property_info.get('epc_score', 'Unknown')
        property_type = property_info.get('property_type', 'Unknown')
        
        # Format price properly
        price_str = f"€{price:,}" if price != 'Unknown' and isinstance(price, (int, float)) else str(price)
        surface_str = f"{surface_area}m²" if surface_area != 'Unknown' else str(surface_area)

        prompt = f"""You are a Belgian real estate expert fluent in Dutch and English, analyzing property descriptions. 

                PROPERTY CONTEXT:
                - Type: {property_type}
                - Location: {location}
                - Price: {price_str}
                - Surface: {surface_str}
                - EPC Score: {epc_score}

                DESCRIPTION TO ANALYZE (may be in Dutch):
                {description}

                IMPORTANT: The description above may be in Dutch. Please read and understand it fully, then provide your analysis in ENGLISH only. Translate any Dutch terms or concepts into clear English.

                Please analyze this property description and provide a structured assessment in JSON format with the following sections:

                {{
                  "pros": [
                    "List of positive aspects mentioned in the description",
                    "Include location benefits, property features, condition, etc."
                  ],
                  "cons": [
                    "List of potential concerns or limitations",
                    "Include any mentions of needed repairs, issues, or drawbacks"
                  ],
                  "key_features": [
                    "Most important features highlighted in the description",
                    "Focus on unique selling points"
                  ],
                  "condition_assessment": {{
                    "overall": "excellent/good/fair/needs_work/unknown",
                    "details": "Brief explanation of condition based on description"
                  }},
                  "value_indicators": {{
                    "overpriced_signals": ["Any signs the property might be overpriced"],
                    "good_value_signals": ["Any signs the property offers good value"],
                    "price_justification": "Brief analysis of price vs features mentioned"
                  }},

                  "red_flags": [
                    "Any concerning language or omissions in the description",
                    "Vague descriptions, emphasis on needing work, etc."
                  ],
                  "summary": "2-3 sentence overall assessment of this property",
                  "confidence_score": 0.85
                }}

                DUTCH TO ENGLISH TRANSLATION REFERENCE:
                - woning = property/home, tuin = garden, zolder = attic, kelder = basement
                - badkamer = bathroom, slaapkamer = bedroom, keuken = kitchen, woonkamer = living room
                - terras = terrace, parket = hardwood flooring, tegels = tiles
                - renovatie = renovation, instapklaar = move-in ready, opfrissing = light renovation
                - centrale verwarming = central heating, dubbele beglazing = double glazing
                - rustige buurt = quiet neighborhood, nabij = near, openbaar vervoer = public transport

                CRITICAL REQUIREMENTS:
                1. Respond ONLY with the JSON object - no other text
                2. ALL text in the JSON must be in ENGLISH (translate from Dutch if needed)
                3. Be objective and base analysis strictly on the description provided
                4. Use the translation reference above for common Dutch real estate terms
                5. Maintain Belgian real estate context but explain everything in clear English
                6. NEVER ADD ANY COMMENTS"""

        return prompt
    
    def _query_ollama(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Send a query to Ollama and return the response."""
        if not self.is_available:
            return None
            
        # Configure options based on speed mode
        if self.speed_mode:
            options = {
                "temperature": 0.1,   # Very low for strict format following
                "top_p": 0.8,
                "max_tokens": 800,   # Shorter responses
                "repeat_penalty": 1.6,  # Even higher to prevent repetition
                "num_ctx": 1024,     # Smaller context for focus
                "num_predict": 800,
                "top_k": 20         # Fewer choices for consistency
            }
            timeout = 60  # Shorter timeout in speed mode
        else:
            options = {
                "temperature": 0.1,   # Very low for strict format following
                "top_p": 0.8,
                "max_tokens": 800,
                "repeat_penalty": 1.6,  # Higher to prevent repetition
                "num_ctx": 2048,     # Moderate context
                "num_predict": 1200,
            }
            timeout = 120  # Standard timeout
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": options
        }
        ""

        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    f"{self.ollama_host}/api/generate",
                    json=payload,
                    timeout=120  # E
                )
                
                if response.status_code == 200:
                    result = response.json()
                    raw_response = result.get('response', '').strip()
                    
                    # Validate JSON immediately at API level
                    validated_response = self._validate_and_fix_json_response(raw_response)
                    if validated_response:
                        return validated_response
                    else:
                        print(f"⚠️  Attempt {attempt + 1}: Invalid JSON response, retrying...")
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
                "price_justification": "Analysis failed"
            },
            "investment_potential": {
                "rental_suitability": "unknown",
                "resale_potential": "unknown",
                "renovation_opportunity": "Analysis failed"
            },
            "red_flags": [error_msg],
            "summary": f"Analysis failed: {error_msg}",
            "confidence_score": 0.0,
            "error": error_msg
        }
    
    def analyze_property_description(self, description: str, property_info: Dict) -> Dict[str, Any]:
        """Analyze a single property description and return structured insights."""
        if not description or not description.strip():
            return self._get_error_response("No description provided")
        
        if not self.is_available:
            return self._get_error_response("Ollama not available")
        
        print(f"🤖 Analyzing property description with {self.model_name}...")
        
        # Create the analysis prompt
        prompt = self._create_analysis_prompt(description, property_info)
        
        # Query the LLM
        response = self._query_ollama(prompt)
        
        if not response:
            return self._get_error_response("LLM query failed")
        
        # Parse and return structured analysis
        analysis = self._parse_llm_response(response)
        
        # Add metadata
        analysis['analyzed_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
        analysis['model_used'] = self.model_name
        analysis['description_length'] = len(description)
        
        return analysis
    
    def analyze_multiple_properties(self, properties: List[Dict]) -> List[Dict]:
        """Analyze descriptions for multiple properties with timeout handling."""
        if not self.is_available:
            print("❌ Ollama not available - skipping description analysis")
            return properties
        
        total_properties = len(properties)
        analyzed_properties = []
        successful_analyses = 0
        failed_analyses = 0
        
        print(f"🤖 Starting LLM analysis for {total_properties} properties...")
        print(f"⏱️  Using 120s timeout per property - this may take a while...")
        
        for i, property_data in enumerate(properties, 1):
            print(f"   [{i}/{total_properties}] {property_data.get('location', 'Unknown')}")
            
            description = property_data.get('description', '')
            
            if description and description.strip():
                # Analyze the description
                analysis = self.analyze_property_description(description, property_data)
                
                # Check if analysis was successful
                if analysis.get('error'):
                    print(f"   ❌ Analysis failed: {analysis['error']}")
                    failed_analyses += 1
                    property_data['has_llm_analysis'] = False
                else:
                    print(f"   ✅ Success (confidence: {analysis.get('confidence_score', 0):.2f})")
                    successful_analyses += 1
                    property_data['has_llm_analysis'] = True
                
                # Add analysis to property data
                property_data['llm_analysis'] = analysis
                
                # Extract key insights for easy access (even if failed, for consistency)
                property_data['llm_summary'] = analysis.get('summary', '')
                property_data['llm_pros'] = '; '.join(analysis.get('pros', []))
                property_data['llm_cons'] = '; '.join(analysis.get('cons', []))
                property_data['llm_condition'] = analysis.get('condition_assessment', {}).get('overall', 'unknown')
                property_data['llm_confidence'] = analysis.get('confidence_score', 0.0)
                
                # Shorter delay for faster processing
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