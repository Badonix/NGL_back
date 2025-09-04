import google.generativeai as genai
import json
from datetime import datetime
from config import Config
from .pdf_generator import PDFGenerator

class GeminiFinancialExtractor:
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        self.generation_config = {
            "max_output_tokens": 8192,
            "temperature": 0.1,
        }
        
        self.pdf_generator = PDFGenerator()
        self.financial_prompt = self._get_financial_prompt()
        self.investment_prompt = self._get_investment_prompt()
    
    def extract_financial_data(self, document_text):
        # Try with normal settings first
        for attempt in range(2):
            try:
                if attempt == 0:
                    # First attempt with normal settings
                    config = self.generation_config
                    print("Gemini attempt 1: Normal settings")
                else:
                    # Second attempt with different settings
                    config = {
                        "max_output_tokens": 4096,
                        "temperature": 0.3,
                    }
                    print("Gemini attempt 2: Adjusted settings")
                
                full_prompt = self.financial_prompt + document_text
                response = self.model.generate_content(full_prompt, generation_config=config)
                
                # Enhanced response validation
                if not response:
                    raise ValueError("No response object returned from Gemini")
                
                # Enhanced text extraction handling multi-part responses
                response_text = self._extract_response_text(response)
                if not response_text:
                    raise ValueError("No text content in Gemini response")
                
                # Log the raw response length for debugging
                print(f"Gemini response length: {len(response_text)} characters")
                
                # Additional validation - check if response looks like it might contain JSON
                if len(response_text.strip()) < 10:
                    raise ValueError(f"Response too short: '{response_text.strip()}'")
                
                financial_data = self._parse_response(response_text)
                pdf_result = self._generate_pdf_if_needed(financial_data)
                
                return {
                    "success": True,
                    "data": financial_data,
                    "pdf_result": pdf_result
                }
                
            except Exception as e:
                print(f"Gemini attempt {attempt + 1} failed: {str(e)}")
                if attempt == 1:  # Last attempt
                    # Enhanced error information
                    error_info = {
                        "success": False,
                        "error": f"Gemini API error (all attempts failed): {str(e)}",
                        "raw_response": None
                    }
                    
                    # If we have a response object, try to get some debug info
                    try:
                        if 'response' in locals() and response:
                            response_text = self._extract_response_text(response)
                            error_info["raw_response"] = response_text[:1000] if response_text else "No text content"
                            if hasattr(response, 'candidates'):
                                error_info["candidates_count"] = len(response.candidates) if response.candidates else 0
                    except:
                        pass
                    
                    return error_info
                # Continue to next attempt
                continue
    
    def analyze_investment_data(self, document_text):
        try:
            full_prompt = self.investment_prompt + document_text
            response = self.model.generate_content(full_prompt, generation_config=self.generation_config)
            
            if not response.text:
                raise ValueError("No response generated from Gemini")
            
            investment_data = self._parse_investment_response(response.text)
            
            return {
                "success": True,
                "data": investment_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini API error: {str(e)}",
                "raw_response": None
            }
    
    def check_investment_sufficiency(self, document_text):
        """
        Check investment data sufficiency using Gemini
        """
        try:
            sufficiency_prompt = self._get_sufficiency_prompt() + document_text
            response = self.model.generate_content(sufficiency_prompt, generation_config=self.generation_config)
            
            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("No text content in Gemini response")
            
            sufficiency_data = self._parse_sufficiency_response(response_text)
            
            return {
                "success": True,
                **sufficiency_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini API error: {str(e)}"
            }
    
    def _parse_response(self, response_text):
        try:
            # First check if we have any response at all
            if not response_text or response_text.strip() == "":
                raise ValueError("Empty response from Gemini API")
            
            response_text = response_text.strip()
            
            # Enhanced JSON extraction with multiple fallback methods
            json_text = self._extract_json_content(response_text)
            
            if not json_text:
                raise ValueError(f"No valid JSON found in response. Raw response: {response_text[:200]}...")
            
            # Clean the JSON text
            json_text = json_text.replace('\\n', '\n').replace('\\"', '"')
            
            # Fix common JSON issues
            json_text = self._fix_common_json_issues(json_text)
            
            if not json_text.rstrip().endswith('}'):
                json_text = self._fix_truncated_json(json_text)
            
            parsed_data = json.loads(json_text)
            
            # Convert string numbers to actual numbers in financial analysis
            if 'financial_analysis' in parsed_data:
                parsed_data['financial_analysis'] = self._convert_string_numbers(parsed_data['financial_analysis'])
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            # Try to extract partial data as fallback
            try:
                partial_data = self._extract_partial_data(response_text)
                if partial_data:
                    return partial_data
            except:
                pass
            
            # If all else fails, provide a detailed error with the raw response
            raise ValueError(f"Failed to parse JSON response from Gemini: {str(e)}. Raw response: {response_text[:500]}...")
        except Exception as e:
            raise ValueError(f"Response parsing error: {str(e)}. Raw response: {response_text[:500]}...")
    
    def _extract_response_text(self, response):
        """Extract text from Gemini response handling both simple and multi-part responses"""
        try:
            # Try the simple accessor first
            if hasattr(response, 'text') and response.text:
                return response.text
        except ValueError:
            # If simple accessor fails, use the parts accessor
            pass
        
        try:
            # Handle multi-part responses
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        # Concatenate all text parts
                        text_parts = []
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)
                        return ''.join(text_parts)
        except Exception as e:
            print(f"Error extracting response text: {e}")
        
        return None

    def _extract_json_content(self, response_text):
        """Enhanced JSON extraction with multiple fallback methods"""
        # Method 1: Standard markdown code blocks
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                return response_text[start:end].strip()
        
        # Method 2: Generic code blocks
        if response_text.startswith("```") and response_text.endswith("```"):
            return response_text[3:-3].strip()
        
        # Method 3: Look for JSON-like structure
        if "{" in response_text and "}" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            return response_text[start:end]
        
        # Method 4: Return as-is (maybe it's just JSON without formatting)
        return response_text
    
    def _fix_common_json_issues(self, json_text):
        """Fix common JSON formatting issues"""
        import re
        
        # Remove any trailing commas before closing braces/brackets
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        
        # Remove extra commas after closing braces (common Gemini issue)
        json_text = re.sub(r'}(\s*),(\s*)"', r'}\2"', json_text)
        
        # Fix double commas
        json_text = re.sub(r',,+', ',', json_text)
        
        # Fix missing commas between objects/arrays (but be careful not to break strings)
        # This is a simple pattern - may need refinement
        json_text = re.sub(r'}(\s+)"', r'},\1"', json_text)
        json_text = re.sub(r'](\s+)"', r'],\1"', json_text)
        json_text = re.sub(r'(\d)(\s+)"', r'\1,\2"', json_text)
        json_text = re.sub(r'null(\s+)"', r'null,\1"', json_text)
        
        return json_text

    def _convert_string_numbers(self, data):
        """Convert string numbers to actual numbers in the financial data structure"""
        if isinstance(data, dict):
            converted = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    converted[key] = self._convert_string_numbers(value)
                elif isinstance(value, str):
                    # Handle various string number formats
                    if value == "null" or value == "None" or value == "":
                        converted[key] = None
                    elif value.isdigit():
                        converted[key] = int(value)
                    elif value.replace('.', '').replace('-', '').replace(',', '').isdigit():
                        # Remove commas and convert to float
                        clean_value = value.replace(',', '')
                        converted[key] = float(clean_value)
                    else:
                        converted[key] = value
                else:
                    converted[key] = value
            return converted
        return data
    
    def _fix_truncated_json(self, json_text):
        last_brace = json_text.rfind('}')
        if last_brace > 0:
            brace_count = 0
            for i in range(last_brace, -1, -1):
                if json_text[i] == '}':
                    brace_count += 1
                elif json_text[i] == '{':
                    brace_count -= 1
                    if brace_count == 0:
                        return json_text[:i+1] + '}'
        return json_text
    
    def _extract_partial_data(self, json_text):
        try:
            if '"financial_analysis"' in json_text:
                start_idx = json_text.find('"financial_analysis"')
                brace_start = json_text.find('{', start_idx)
                if brace_start > 0:
                    brace_count = 0
                    end_idx = -1
                    for i in range(brace_start, len(json_text)):
                        if json_text[i] == '{':
                            brace_count += 1
                        elif json_text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i
                                break
                    
                    if end_idx > 0:
                        partial_json = json_text[brace_start:end_idx+1]
                        financial_data = json.loads(partial_json)
                        return {"financial_analysis": financial_data}
        except:
            pass
        return None
    
    def _generate_pdf_if_needed(self, financial_data):
        if "summerized_data" not in financial_data or not financial_data["summerized_data"]:
            return None
        
        pdf_filename = f"financial_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = f"{Config.PDF_FOLDER}/{pdf_filename}"
        
        pdf_result = self.pdf_generator.generate_summary_pdf(
            financial_data["summerized_data"], 
            pdf_path
        )
        
        if pdf_result["success"]:
            pdf_result["public_url"] = f"/pdfs/{pdf_filename}"
        
        return pdf_result
    
    def _get_financial_prompt(self):
        return """
You are a financial data extraction expert specializing in Georgian financial statements. Analyze the provided document and extract the specific financial line items listed below in a structured JSON format.

**REQUIRED EXTRACTION - These specific line items MUST be found and extracted:**

**A. Income Statement (IS) - REQUIRED:**
- Revenue/Sales (შემოსავალი რეალიზაციიდან)
- COGS (რეალიზებული პროდუქციის თვითღირებულება)
- Gross Profit (calculated)
- Operating Expenses (საოპერაციო ხარჯები / გაყიდვების & ადმინისტრაციული ხარჯები)
- Depreciation & Amortization (ამორტიზაცია და ცვეთა)
- Other Operating Income/Expense (სხვა საოპერაციო შემოსავლები/ხარჯები)
- Operating Profit/EBIT (საოპერაციო მოგება)
- Interest Expense (საპროცენტო ხარჯები)
- Interest Income (საპროცენტო შემოსავლები)
- Foreign Exchange Gains/Losses (კურსთაშორისი სხვაობები)
- Profit Before Tax/EBT (მოგება გადასახადამდე)
- Income Tax Expense (მოგების გადასახადი)
- Net Income (წმინდა მოგება)

**B. Balance Sheet (BS) - REQUIRED:**
- Cash & Equivalents (ფულადი სახსრები)
- Accounts Receivable (ვალდებულებები დებიტორებისგან)
- Inventory (მარაგები)
- Other Current Assets (სხვა მიმდინარე აქტივები)
- Property, Plant & Equipment/PP&E (ქონება, მცენარეები და ტექნიკა)
- Intangible Assets (არამატერიალური აქტივები)
- Accounts Payable (ვალდებულებები მომწოდებლების მიმართ)
- Short-term Debt (მოკლევადიანი სესხები)
- Long-term Debt (გრძელვადიანი სესხები)
- Deferred Tax Liabilities (გადავადებული გადასახადები)
- Shareholder's Equity (კაპიტალი)

**C. Cash Flow Statement (CF) - REQUIRED:**
- Cash Flow from Operations/CFO (საოპერაციო საქმიანობიდან მიღებული ფულადი ნაკადები)
- Taxes Paid (გადახდილი მოგების გადასახადი)
- Interest Paid (გადახდილი საპროცენტო ხარჯები)
- Capital Expenditures/CapEx (ინვესტიციები ქონებაში, მცენარეებში, ტექნიკაში)
- Changes in Working Capital (სამუშაო კაპიტალის ცვლილებები)
- Free Cash Flow/FCF (calculated)

Besides it, save all available financial data to the summerized data field, including summerized info about company, everthing important, but do more focus on financial data, as it is a financial summary.

Please provide the response in the following JSON structure:

{
    "summerized_data": {
    // All data including important financial data, company info etc. make more focus on financial data 
    },
  "financial_analysis": {
    "income_statement": {
      "revenue_sales": {"2022": "number", "2023": "number"},
      "cogs": {"2022": "number", "2023": "number"},
      "gross_profit": {"2022": "number", "2023": "number", "note": "calculated"},
      "operating_expenses": {"2022": "number", "2023": "number"},
      "depreciation_amortization": {"2022": "number", "2023": "number"},
      "other_operating_income_expense": {"2022": "number", "2023": "number"},
      "operating_profit_ebit": {"2022": "number", "2023": "number"},
      "interest_expense": {"2022": "number", "2023": "number"},
      "interest_income": {"2022": "number", "2023": "number"},
      "foreign_exchange_gains_losses": {"2022": "number", "2023": "number"},
      "profit_before_tax_ebt": {"2022": "number", "2023": "number"},
      "income_tax_expense": {"2022": "number", "2023": "number"},
      "net_income": {"2022": "number", "2023": "number"}
    },
    "balance_sheet": {
      "cash_equivalents": {"2022": "number", "2023": "number"},
      "accounts_receivable": {"2022": "number", "2023": "number"},
      "inventory": {"2022": "number", "2023": "number"},
      "other_current_assets": {"2022": "number", "2023": "number"},
      "ppe": {"2022": "number", "2023": "number"},
      "intangible_assets": {"2022": "number", "2023": "number"},
      "accounts_payable": {"2022": "number", "2023": "number"},
      "short_term_debt": {"2022": "number", "2023": "number"},
      "long_term_debt": {"2022": "number", "2023": "number"},
      "deferred_tax_liabilities": {"2022": "number", "2023": "number"},
      "shareholders_equity": {"2022": "number", "2023": "number"}
    },
    "cash_flow_statement": {
      "cash_flow_from_operations": {"2022": "number", "2023": "number"},
      "taxes_paid": {"2022": "number", "2023": "number"},
      "interest_paid": {"2022": "number", "2023": "number"},
      "capital_expenditures": {"2022": "number", "2023": "number"},
      "changes_in_working_capital": {"2022": "number", "2023": "number"},
      "free_cash_flow": {"2022": "number", "2023": "number", "note": "calculated"}
    }
  }
}

**CRITICAL FORMATTING REQUIREMENTS FOR JSON RESPONSE:**
1. **MUST RETURN VALID JSON ONLY** - No explanatory text before or after the JSON
2. **Start response with { and end with }** - No markdown code blocks needed
3. **Use exact field names as shown** in the example structure above
4. **Numbers as actual numbers, not strings** (e.g., 1500000 not "1,500,000")
5. **All years should be strings** (e.g., "2023", "2022")
6. **Missing data should be null** (not "N/A" or empty string)

**IMPORTANT:** Extract data for ALL available years found in the document, not just the example years shown above. Use the actual years from the financial statements (e.g., 2019, 2020, 2021, 2022, 2023, 2024, etc.). If any information is not available for a specific year, use null for that field. Include extraction_notes for any items that could not be found or extracted. Be precise with numbers and focus on extracting quantitative data that would be valuable for investment analysis.

RETURN ONLY THE JSON OBJECT - NO OTHER TEXT.

Document content to analyze:
"""
    
    def _parse_investment_response(self, response_text):
        try:
            response_text = response_text.strip()
            
            # Try to find JSON content between ```json and ```
            if "```json" in response_text and "```" in response_text:
                start_marker = "```json"
                end_marker = "```"
                start_index = response_text.find(start_marker) + len(start_marker)
                end_index = response_text.find(end_marker, start_index)
                json_content = response_text[start_index:end_index].strip()
            elif "{" in response_text and "}" in response_text:
                # Try to extract JSON directly
                start_index = response_text.find("{")
                end_index = response_text.rfind("}") + 1
                json_content = response_text[start_index:end_index]
            else:
                # Return raw text if no JSON structure found
                return {
                    "investment_analysis": {
                        "summary": response_text,
                        "recommendations": [],
                        "risk_assessment": "Analysis provided as text",
                        "opportunities": [],
                        "market_analysis": response_text
                    }
                }
            
            parsed_data = json.loads(json_content)
            return parsed_data
            
        except json.JSONDecodeError as e:
            return {
                "investment_analysis": {
                    "summary": f"Failed to parse structured analysis. Raw response: {response_text[:500]}...",
                    "recommendations": [],
                    "risk_assessment": "JSON parsing error",
                    "opportunities": [],
                    "market_analysis": response_text,
                    "parse_error": str(e)
                }
            }
        except Exception as e:
            return {
                "investment_analysis": {
                    "summary": f"Error processing investment analysis: {str(e)}",
                    "recommendations": [],
                    "risk_assessment": "Processing error",
                    "opportunities": [],
                    "market_analysis": response_text if 'response_text' in locals() else "No response",
                    "error": str(e)
                }
            }
    
    def _get_investment_prompt(self):
        return """
You are a professional investment analyst and financial advisor. Your task is to analyze the provided investment data, market information, financial projections, or company reports and provide comprehensive investment insights.

Analyze the provided content and extract the following information:

1. **Investment Summary**: Key investment thesis and overall assessment
2. **Market Analysis**: Market size, growth potential, competitive landscape
3. **Financial Projections**: Revenue forecasts, profitability expectations, cash flow analysis
4. **Risk Assessment**: Key risks, market risks, operational risks, financial risks
5. **Investment Opportunities**: Growth drivers, strategic advantages, market position
6. **Recommendations**: Investment rating, target price, time horizon, rationale
7. **Key Metrics**: Valuation multiples, financial ratios, performance indicators

Please provide the response in the following JSON structure:

{
    "investment_analysis": {
        "summary": "Brief investment thesis and key findings",
        "market_analysis": {
            "market_size": "Market size and growth potential",
            "competitive_landscape": "Competition analysis",
            "growth_drivers": ["Key growth factors"],
            "market_trends": ["Relevant market trends"]
        },
        "financial_analysis": {
            "revenue_projections": {
                "current": "number or description",
                "projected": "future projections",
                "growth_rate": "expected growth rate"
            },
            "profitability": {
                "current_margins": "current profit margins",
                "projected_margins": "future margin expectations",
                "ebitda_projections": "EBITDA forecasts"
            },
            "cash_flow": {
                "operating_cash_flow": "OCF analysis",
                "free_cash_flow": "FCF projections",
                "capital_requirements": "capex needs"
            }
        },
        "risk_assessment": {
            "overall_risk_level": "Low/Medium/High",
            "key_risks": ["List of main risks"],
            "market_risks": ["Market-specific risks"],
            "operational_risks": ["Operational concerns"],
            "financial_risks": ["Financial stability risks"]
        },
        "opportunities": {
            "growth_opportunities": ["Key growth drivers"],
            "strategic_advantages": ["Competitive advantages"],
            "market_position": "Position in market",
            "expansion_potential": "Growth potential"
        },
        "valuation": {
            "current_valuation": "Current value assessment",
            "target_valuation": "Target price/value",
            "valuation_method": "Methodology used",
            "key_multiples": {
                "p_e_ratio": "P/E analysis",
                "ev_ebitda": "EV/EBITDA analysis",
                "price_to_sales": "P/S analysis"
            }
        },
        "recommendations": {
            "investment_rating": "Buy/Hold/Sell or similar",
            "confidence_level": "High/Medium/Low",
            "time_horizon": "Short/Medium/Long term",
            "rationale": "Detailed reasoning for recommendation",
            "key_catalysts": ["Events that could drive performance"],
            "price_targets": {
                "bull_case": "Optimistic scenario",
                "base_case": "Most likely scenario",
                "bear_case": "Conservative scenario"
            }
        },
        "key_metrics": {
            "financial_ratios": {},
            "performance_indicators": {},
            "comparison_benchmarks": {}
        }
    }
}

**IMPORTANT:** 
- Focus on extracting quantitative data where available
- Provide clear investment insights and actionable recommendations
- Assess risks thoroughly and honestly
- Include market context and competitive analysis
- If information is missing, note it explicitly
- Adapt the analysis to the type of investment data provided (equity, real estate, bonds, etc.)

Investment data to analyze:
"""
    
    def _get_sufficiency_prompt(self):
        return """
You are a professional investment analyst. Analyze the provided investment data comprehensively and rate its sufficiency for making sound investment decisions.

The data may include:
- Previous financial analysis results (financial statements, ratios, trends)
- Previous valuation analysis (DCF models, comparable analysis, market multiples)
- New files with additional information
- Manual input with supplementary data

Evaluate the completeness and quality across these key investment decision areas:

1. **Financial Foundation** (25% weight)
   - Historical financial statements (3+ years ideal)
   - Key financial ratios and trends
   - Cash flow analysis and projections
   - Debt structure and covenant compliance

2. **Valuation Analysis** (20% weight)
   - Multiple valuation methodologies (DCF, comps, precedent transactions)
   - Sensitivity analysis and scenario modeling
   - Market multiples and peer comparison
   - Asset-based valuation if applicable

3. **Business Understanding** (20% weight)
   - Business model and revenue streams
   - Competitive positioning and advantages
   - Market size and growth potential
   - Customer base and concentration

4. **Management & Governance** (15% weight)
   - Management team experience and track record
   - Board composition and governance structure
   - Strategic vision and execution capability
   - Insider ownership and alignment

5. **Risk Assessment** (10% weight)
   - Market and industry risks
   - Operational and execution risks
   - Financial and leverage risks
   - Regulatory and compliance risks

6. **Growth & Strategy** (10% weight)
   - Growth strategy and expansion plans
   - Capital allocation priorities
   - Innovation and R&D capabilities
   - Market opportunity and addressable market

Rate the overall sufficiency considering that institutional-quality investment decisions typically require 80%+ data completeness.

Provide your response in this exact JSON format:

{
    "sufficiency_percentage": <number 0-100>,
    "missing_data": [
        "Specific missing data point 1",
        "Specific missing data point 2"
    ],
    "recommendations": [
        "Specific actionable recommendation 1",
        "Specific actionable recommendation 2"
    ],
    "critical_gaps": [
        "Critical gap 1 that prevents investment decision",
        "Critical gap 2 that significantly impacts risk assessment"
    ]
}

**CRITICAL INSTRUCTIONS:**
- Return ONLY the JSON object above, no additional text
- Be specific about what data is missing (not generic statements)
- Provide actionable recommendations for obtaining missing information
- Critical gaps should be showstoppers that prevent making the investment decision
- Consider the quality and recency of provided data
- If comprehensive data is provided across multiple sources, reflect that in a higher percentage

Investment data to analyze:
"""
    
    def _parse_sufficiency_response(self, response_text):
        """Parse sufficiency check response from Gemini"""
        try:
            response_text = response_text.strip()
            
            # Try to extract JSON content
            json_text = self._extract_json_content(response_text)
            
            if not json_text:
                # Fallback with default values
                return {
                    "sufficiency_percentage": 50,
                    "missing_data": ["Unable to parse specific missing data"],
                    "recommendations": [response_text[:200] + "..." if len(response_text) > 200 else response_text],
                    "critical_gaps": ["Response parsing error"]
                }
            
            # Clean and parse JSON
            json_text = json_text.replace('\\n', '\n').replace('\\"', '"')
            json_text = self._fix_common_json_issues(json_text)
            
            parsed_data = json.loads(json_text)
            
            # Ensure all required fields exist with defaults
            return {
                "sufficiency_percentage": parsed_data.get("sufficiency_percentage", 50),
                "missing_data": parsed_data.get("missing_data", []),
                "recommendations": parsed_data.get("recommendations", []),
                "critical_gaps": parsed_data.get("critical_gaps", [])
            }
            
        except json.JSONDecodeError as e:
            # Try to extract any valid data from partial JSON
            try:
                # Look for percentage in the raw text
                import re
                percentage_match = re.search(r'"sufficiency_percentage":\s*(\d+)', response_text)
                percentage = int(percentage_match.group(1)) if percentage_match else 40
                
                # Try to extract missing data array
                missing_match = re.search(r'"missing_data":\s*\[(.*?)\]', response_text, re.DOTALL)
                missing_data = []
                if missing_match:
                    # Simple extraction of quoted strings
                    items = re.findall(r'"([^"]*)"', missing_match.group(1))
                    missing_data = items[:10]  # Limit to first 10 items
                
                if not missing_data:
                    missing_data = ["Data parsing incomplete - please try again"]
                
                return {
                    "sufficiency_percentage": percentage,
                    "missing_data": missing_data,
                    "recommendations": ["Response was partially parsed due to formatting issues"],
                    "critical_gaps": ["Partial data extraction performed"]
                }
            except:
                return {
                    "sufficiency_percentage": 40,
                    "missing_data": ["JSON parsing error in response"],
                    "recommendations": [f"Raw response preview: {response_text[:300]}..."],
                    "critical_gaps": ["Model response format error"]
                }
        except Exception as e:
            return {
                "sufficiency_percentage": 30,
                "missing_data": [f"Error parsing response: {str(e)}"],
                "recommendations": ["Please try again"],
                "critical_gaps": ["System error occurred"]
            }
