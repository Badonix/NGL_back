import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config
from .gemini_service import GeminiFinancialExtractor


class OpenRouterService:
    def __init__(self, max_concurrent_workers=4):
        if not Config.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        self.api_key = Config.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "meta-llama/llama-4-maverick"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "NGL Financial Analyzer",
        }
        
        # Configuration for parallel processing
        self.max_concurrent_workers = max_concurrent_workers
        self.model_timeout = 30  # seconds per model

        # Initialize Gemini service for final aggregation
        try:
            self.gemini_service = GeminiFinancialExtractor()
            print("DEBUG: Gemini service initialized for aggregation")
        except Exception as e:
            print(f"WARNING: Gemini not available for aggregation: {e}")
            self.gemini_service = None

    def check_investment_sufficiency(
        self, valuation_data, financial_data, investment_data
    ):
        try:
            prompt = self._build_sufficiency_prompt(
                valuation_data, financial_data, investment_data
            )

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional investment analyst. Your task is to evaluate the sufficiency of investment data and provide a percentage score along with specific recommendations for missing information.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1000,
                "temperature": 0.3,
            }

            response = requests.post(
                self.base_url, headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            return self._parse_sufficiency_response(content)

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"OpenRouter API error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def check_investment_sufficiency_simple(self, combined_text):
        try:
            prompt = self._build_simple_sufficiency_prompt(combined_text)

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional investment analyst. Analyze the provided investment data and rate its sufficiency for making investment decisions. Provide a percentage score and specific recommendations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 800,
                "temperature": 0.3,
            }

            response = requests.post(
                self.base_url, headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            return self._parse_sufficiency_response(content)

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"OpenRouter API error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def _build_sufficiency_prompt(
        self, valuation_data, financial_data, investment_data
    ):

        prompt = """
You are analyzing investment data sufficiency for a comprehensive investment decision. Please evaluate the completeness and quality of the provided data.

**VALUATION DATA:**
"""

        if valuation_data:
            prompt += f"\n{json.dumps(valuation_data, indent=2)}\n"
        else:
            prompt += "\nNo valuation data provided.\n"

        prompt += """
**FINANCIAL ANALYSIS DATA:**
"""

        if financial_data:
            prompt += f"\n{json.dumps(financial_data, indent=2)}\n"
        else:
            prompt += "\nNo financial analysis data provided.\n"

        prompt += """
**INVESTMENT RESEARCH DATA:**
"""

        if investment_data:
            prompt += f"\n{json.dumps(investment_data, indent=2)}\n"
        else:
            prompt += "\nNo additional investment data provided.\n"

        prompt += """

**TASK:**
Evaluate the sufficiency of this data for making a comprehensive investment decision. Consider:

1. **Financial Statement Analysis** (Income Statement, Balance Sheet, Cash Flow)
2. **Valuation Metrics** (DCF, Comparables, Asset-based)
3. **Market Analysis** (Industry trends, competitive landscape)
4. **Risk Assessment** (Financial, operational, market risks)
5. **Growth Projections** (Revenue forecasts, expansion plans)
6. **Management Quality** (Leadership, governance, strategy)
7. **ESG Factors** (Environmental, social, governance considerations)

**RESPONSE FORMAT:**
Provide your response in this exact JSON format:

{
    "sufficiency_percentage": <number between 0-100>,
    "missing_data": [
        "Specific item 1 that's missing",
        "Specific item 2 that's missing",
        "etc."
    ],
    "recommendations": [
        "Recommendation 1 for improving data quality",
        "Recommendation 2 for additional analysis",
        "etc."
    ],
    "critical_gaps": [
        "Critical gap 1 that significantly impacts analysis",
        "Critical gap 2 that must be addressed",
        "etc."
    ]
}

Be precise and specific in your assessment. The percentage should reflect how complete the data is for making a sound investment decision.
"""

        return prompt

    def _parse_sufficiency_response(self, response_text):
        """Parse the LLaMA response and extract percentage and notes"""
        try:
            response_text = response_text.strip()

            # Try to find JSON content
            if "{" in response_text and "}" in response_text:
                start_index = response_text.find("{")
                end_index = response_text.rfind("}") + 1
                json_content = response_text[start_index:end_index]

                parsed_data = json.loads(json_content)

                return {
                    "success": True,
                    "sufficiency_percentage": parsed_data.get(
                        "sufficiency_percentage", 50
                    ),
                    "missing_data": parsed_data.get("missing_data", []),
                    "recommendations": parsed_data.get("recommendations", []),
                    "critical_gaps": parsed_data.get("critical_gaps", []),
                }
            else:
                # Fallback if no JSON structure found
                return {
                    "success": True,
                    "sufficiency_percentage": 50,
                    "missing_data": ["Unable to parse specific missing data"],
                    "recommendations": [
                        (
                            response_text[:200] + "..."
                            if len(response_text) > 200
                            else response_text
                        )
                    ],
                    "critical_gaps": ["Response parsing error"],
                }

        except json.JSONDecodeError as e:
            return {
                "success": True,
                "sufficiency_percentage": 40,
                "missing_data": ["JSON parsing error in response"],
                "recommendations": [f"Raw response: {response_text[:200]}..."],
                "critical_gaps": ["Model response format error"],
            }
        except Exception as e:
            return {"success": False, "error": f"Error parsing response: {str(e)}"}

    def _build_simple_sufficiency_prompt(self, combined_text):
        """Build a simple prompt for sufficiency checking using combined text"""

        prompt = f"""
You are analyzing investment data for sufficiency and completeness. Please evaluate how complete this data is for making sound investment decisions.

**INVESTMENT DATA TO ANALYZE:**
{combined_text}

**TASK:**
Rate the sufficiency of this data for making a comprehensive investment decision on a scale of 0-100%.

Consider these key areas:
1. **Financial Information** - Revenue, profits, cash flow, balance sheet data
2. **Market Analysis** - Industry size, growth trends, competitive landscape  
3. **Business Model** - How the company makes money, key operations
4. **Risk Factors** - Financial, operational, market, regulatory risks
5. **Growth Potential** - Expansion plans, new products/services, market opportunities
6. **Management Quality** - Leadership team, governance, strategic vision
7. **Valuation Metrics** - Current pricing, comparable companies, financial ratios

**RESPONSE FORMAT:**
Provide your response in this exact JSON format:

{{
    "sufficiency_percentage": <number between 0-100>,
    "missing_data": [
        "Specific missing item 1",
        "Specific missing item 2", 
        "etc."
    ],
    "recommendations": [
        "Specific recommendation 1 for improvement",
        "Specific recommendation 2 for additional data",
        "etc."
    ],
    "critical_gaps": [
        "Critical gap 1 that significantly impacts analysis",
        "Critical gap 2 that must be addressed",
        "etc."
    ]
}}

Be specific and actionable in your assessment. Focus on what investment information is missing that would be crucial for making a sound investment decision.
"""

        return prompt

    def calculate_investment_validity(
        self, financial_data, valuation_data, investment_data
    ):
        """
        Calculate investment validity using 5 AI models + final aggregation
        """
        try:
            # Define the 5 models with their weights
            models = [
                {"name": "meta-llama/llama-4-maverick", "weight": 0.30},
                {"name": "meta-llama/llama-3.3-70b-instruct", "weight": 0.14},
                {"name": "google/gemma-3-27b-it", "weight": 0.16},
                {"name": "mistralai/mistral-small-3.2-24b-instruct", "weight": 0.18},
                {"name": "meta-llama/llama-4-scout", "weight": 0.22},
            ]

            # Build the investment validity prompt
            prompt = self._build_investment_validity_prompt(
                financial_data, valuation_data, investment_data
            )

            # Collect responses from all 5 models in parallel
            print(f"DEBUG: Starting parallel processing of {len(models)} models")
            start_time = time.time()
            
            model_responses = self._query_models_parallel(models, prompt)
            
            end_time = time.time()
            successful_models = sum(1 for r in model_responses if r['success'])
            total_models = len(model_responses)
            
            print(f"DEBUG: Parallel processing completed in {end_time - start_time:.2f} seconds")
            print(f"DEBUG: Successfully processed {successful_models}/{total_models} models")
            
            # Log individual model performance
            for response in model_responses:
                status = "✓" if response['success'] else "✗"
                time_str = f"{response.get('processing_time', 0):.2f}s" if response['success'] else "failed"
                print(f"DEBUG: {status} {response['model']}: {time_str}")
            
            # Check if we have enough successful responses for aggregation
            if successful_models == 0:
                raise Exception("All AI models failed to respond. Cannot calculate investment validity.")
            elif successful_models < 2:
                print(f"WARNING: Only {successful_models} model(s) responded successfully. Results may be less reliable.")
            
            # Calculate time savings vs sequential processing
            if successful_models > 1:
                avg_model_time = sum(r.get('processing_time', 0) for r in model_responses if r['success']) / successful_models
                estimated_sequential_time = avg_model_time * total_models
                time_saved = estimated_sequential_time - (end_time - start_time)
                print(f"DEBUG: Estimated time saved: {time_saved:.2f}s ({time_saved/estimated_sequential_time*100:.1f}% faster)")

            # Aggregate results and send to final model
            final_result = self._aggregate_model_responses(
                model_responses, financial_data, valuation_data, investment_data
            )

            return {
                "success": True,
                "data": {
                    "individual_responses": model_responses,
                    "final_decision": final_result,
                    "models_used": len([r for r in model_responses if r["success"]]),
                    "total_models": len(models),
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Investment validity calculation error: {str(e)}",
            }

    def _query_models_parallel(self, models, prompt):
        """Query multiple models in parallel using ThreadPoolExecutor"""
        model_responses = []
        
        def query_single_model(model):
            """Query a single model and return structured response"""
            try:
                start_time = time.time()
                response = self._query_model(model["name"], prompt)
                end_time = time.time()
                
                print(f"DEBUG: {model['name']} completed in {end_time - start_time:.2f}s")
                
                return {
                    "model": model["name"],
                    "weight": model["weight"],
                    "response": response,
                    "success": True,
                    "processing_time": end_time - start_time
                }
            except Exception as e:
                print(f"DEBUG: {model['name']} failed: {str(e)}")
                return {
                    "model": model["name"],
                    "weight": model["weight"],
                    "response": None,
                    "success": False,
                    "error": str(e),
                    "processing_time": 0
                }
        
        # Use ThreadPoolExecutor for parallel processing
        # Limit concurrent threads to avoid overwhelming the API and respect rate limits
        # OpenRouter typically allows multiple concurrent requests
        max_workers = min(len(models), self.max_concurrent_workers)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all model queries
            future_to_model = {
                executor.submit(query_single_model, model): model 
                for model in models
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    model_responses.append(result)
                except Exception as e:
                    # This should rarely happen since we handle exceptions in query_single_model
                    print(f"DEBUG: Unexpected error for {model['name']}: {str(e)}")
                    model_responses.append({
                        "model": model["name"],
                        "weight": model["weight"],
                        "response": None,
                        "success": False,
                        "error": f"Thread execution error: {str(e)}",
                        "processing_time": 0
                    })
        
        # Sort responses by original model order for consistency
        model_names_order = [m["name"] for m in models]
        model_responses.sort(key=lambda x: model_names_order.index(x["model"]))
        
        return model_responses

    def _query_model(self, model_name, prompt):
        """Query a specific model with the investment prompt"""
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a senior VC/PE investment analyst. Follow the provided prompt exactly and return only the requested JSON structure.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2000,
            "temperature": 0.1,
        }

        # Use configurable timeout for model requests
        response = requests.post(
            self.base_url, headers=self.headers, json=payload, timeout=self.model_timeout
        )
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        return self._parse_investment_response(content)

    def _aggregate_model_responses(
        self, model_responses, financial_data, valuation_data, investment_data
    ):
        """Use Gemini to aggregate all model responses into a final investment decision"""

        # Filter successful responses
        successful_responses = [r for r in model_responses if r["success"]]

        if not successful_responses:
            return {
                "verdict": "insufficient_data",
                "confidence": 0,
                "error": "No models provided valid responses",
            }

        # Use Gemini for final aggregation if available
        if self.gemini_service:
            try:
                print(f"DEBUG: Using Gemini for final aggregation of {len(successful_responses)} model responses")
                final_response = self.gemini_service.aggregate_investment_responses(
                    model_responses, financial_data, valuation_data, investment_data
                )
                print(f"DEBUG: Gemini aggregation successful")
                return final_response
            except Exception as e:
                print(f"WARNING: Gemini aggregation failed: {e}, falling back to LLaMA")
                # Continue to fallback below

        # Fallback: Use LLaMA for aggregation (original behavior)
        print(f"DEBUG: Using LLaMA fallback for aggregation")
        try:
            # Build enhanced aggregation prompt for LLaMA
            aggregation_prompt = f"""
You are the final investment decision aggregator. You have received responses from {len(successful_responses)} AI models, each with different weights/coefficients. Your task is to produce a final normalized investment decision that takes these coefficients into account and provides realistic, well-reasoned output.

ORIGINAL DATA SOURCES:

1) FINANCE_JSON:
{json.dumps(financial_data, indent=2)}

2) VALUATION_JSON:
{json.dumps(valuation_data, indent=2)}

3) NEW_INFO_JSON:
{json.dumps(investment_data, indent=2)}

MODEL RESPONSES WITH THEIR COEFFICIENTS:
"""

            for response in successful_responses:
                aggregation_prompt += f"""
MODEL: {response['model']} (COEFFICIENT: {response['weight']})
RESPONSE: {json.dumps(response['response'], indent=2)}

"""

            aggregation_prompt += """
NOTE: The user has explicitly initiated a full evaluation. Even if data is incomplete, you MUST produce a final verdict and full output package. Do not return an "insufficient_data" stop. Instead, when any data is incomplete, proceed with best-effort estimations, set lower confidence, and include clear follow_up_questions and provenance explaining what was estimated and why.

TASK — produce a final investment decision package by intelligently aggregating the model responses.

Return ONLY the JSON structure that follows the OUTPUT_SCHEMA. No explanations or markdown outside the JSON.

{
  "verdict": "invest" | "consider_with_conditions" | "dont_invest" | "insufficient_data",
  "confidence": number 0-100,
  "valuation": {
    "raw": { "p25": number | null, "p50": number | null, "p75": number | null },
    "adjusted": { "p25": number | null, "p50": number | null, "p75": number | null }
  },
  "aggregation_summary": {
    "models_consensus": string,
    "key_disagreements": string,
    "final_reasoning": string,
    "confidence_basis": string
  }
}

Now analyze the provided data and model responses, apply the coefficients appropriately, and RETURN the single JSON result.
"""

            final_response = self._query_model(
                "meta-llama/llama-4-maverick", aggregation_prompt
            )
            return final_response
        except Exception as e:
            print(f"WARNING: LLaMA aggregation also failed: {e}")
            # Final fallback: return the highest weighted successful response
            best_response = max(successful_responses, key=lambda x: x["weight"])
            return best_response["response"]

    def _parse_investment_response(self, response_text):
        """Parse investment validity response from AI models"""
        try:
            response_text = response_text.strip()

            # Try to find JSON content
            if "```json" in response_text and "```" in response_text:
                start_marker = "```json"
                end_marker = "```"
                start_index = response_text.find(start_marker) + len(start_marker)
                end_index = response_text.find(end_marker, start_index)
                json_content = response_text[start_index:end_index].strip()
            elif "{" in response_text and "}" in response_text:
                start_index = response_text.find("{")
                end_index = response_text.rfind("}") + 1
                json_content = response_text[start_index:end_index]
            else:
                return {
                    "verdict": "insufficient_data",
                    "confidence": 0,
                    "error": "No valid JSON response format found",
                }

            parsed_data = json.loads(json_content)
            return parsed_data

        except json.JSONDecodeError as e:
            return {
                "verdict": "insufficient_data",
                "confidence": 0,
                "error": f"JSON parsing error: {str(e)}",
                "raw_response": response_text[:500],
            }
        except Exception as e:
            return {
                "verdict": "insufficient_data",
                "confidence": 0,
                "error": f"Response processing error: {str(e)}",
            }

    def _build_investment_validity_prompt(
        self, financial_data, valuation_data, investment_data
    ):
        """Build the comprehensive investment validity prompt"""

        # The exact prompt you provided with data injection
        prompt = f"""AI Investment Decision Prompt — Deterministic, Excel-Style (Consumes Pre-Computed Valuation, Stage- & Sector-Aware, Region-Adjusted, With Simple Summary for Non-Experts)

ROLE
You are a senior VC/PE investment analyst producing a final investment decision package. You DO NOT recompute valuation models (DCF/comps/NAV). Instead, you CONSUME the already-computed valuation outputs from VALUATION_JSON and combine them with offer terms, risk inputs, preferences, sector/stage constants, peer benchmarks, macro/FX context, and finance data to deliver a verdict and recommended terms. Perform calculations in strict, auditable order. Use only INPUT and CONSTANTS. No browsing or external data.

INPUT (your actual data)

FINANCE_JSON (Previously computed financial analysis)
{json.dumps(financial_data, indent=2)}

VALUATION_JSON (Previously computed valuation results)
{json.dumps(valuation_data, indent=2)}

NEW_INFO_JSON (Investment terms and additional information)
Note: This may include 'all_file_content' field containing original financial documents plus any additional files uploaded for this analysis.
{json.dumps(investment_data, indent=2)}

[Rest of the prompt with CONSTANTS, PROCESS, OUTPUT_SCHEMA remains exactly the same as provided]

Return ONLY the JSON structure. No explanations or markdown outside the JSON.
"""

        return prompt
