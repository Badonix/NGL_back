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
        self.model = genai.GenerativeModel("gemini-2.5-flash-lite")

        self.generation_config = {
            "max_output_tokens": 16384,
            "temperature": 0.1,
        }

        self.pdf_generator = PDFGenerator()
        self.financial_prompt = self._get_financial_prompt()
        self.investment_prompt = self._get_investment_prompt()

    def extract_financial_data(self, document_text):
        for attempt in range(2):
            try:
                if attempt == 0:
                    config = self.generation_config
                    print("Gemini attempt 1: Normal settings")
                else:
                    config = {
                        "max_output_tokens": 4096,
                        "temperature": 0.3,
                    }
                    print("Gemini attempt 2: Adjusted settings")

                full_prompt = self.financial_prompt + document_text
                
                print(f"DEBUG: Sending {len(document_text)} characters to Gemini")
                print(f"DEBUG: Document contains {document_text.count('--- FILE:')} file separators")
                
                response = self.model.generate_content(
                    full_prompt, generation_config=config
                )

                if not response:
                    raise ValueError("No response object returned from Gemini")

                response_text = self._extract_response_text(response)
                if not response_text:
                    raise ValueError("No text content in Gemini response")

                print(f"Gemini response length: {len(response_text)} characters")
                
                if len(response_text.strip()) < 10:
                    raise ValueError(f"Response too short: '{response_text.strip()}'")

                financial_data = self._parse_response(response_text)
                
                print(f"DEBUG: Parsed financial_analysis keys: {financial_data.get('financial_analysis', {}).keys() if 'financial_analysis' in financial_data else 'No financial_analysis'}")
                if 'financial_analysis' in financial_data and 'income_statement' in financial_data['financial_analysis']:
                    revenue_years = list(financial_data['financial_analysis']['income_statement'].get('revenue_sales', {}).keys())
                    print(f"DEBUG: Revenue data extracted for years: {revenue_years}")
                    
                    # Log a sample of the raw response to see what AI is returning
                    print(f"DEBUG: Raw response preview: {response_text[:500]}...")
                    if "2021" in response_text or "2022" in response_text:
                        print(f"DEBUG: Found 2021/2022 in raw response but not in parsed data!")
                    
                    # Check all financial statement sections for years
                    for section_name, section_data in financial_data['financial_analysis'].items():
                        if isinstance(section_data, dict):
                            all_years = set()
                            for item_name, item_data in section_data.items():
                                if isinstance(item_data, dict):
                                    all_years.update(item_data.keys())
                            if all_years:
                                print(f"DEBUG: {section_name} contains years: {sorted(all_years)}")
                
                # Check summarized_data for year mentions
                if 'summerized_data' in financial_data:
                    summarized_text = str(financial_data['summerized_data'])
                    years_in_summary = []
                    for year in ['2021', '2022', '2023', '2024', '2025']:
                        if year in summarized_text:
                            years_in_summary.append(year)
                    print(f"DEBUG: summarized_data mentions years: {years_in_summary}")
                    print(f"DEBUG: summarized_data length: {len(summarized_text)} characters")
                pdf_result = self._generate_pdf_if_needed(financial_data)

                return {
                    "success": True,
                    "data": financial_data,
                    "pdf_result": pdf_result,
                }

            except Exception as e:
                print(f"Gemini attempt {attempt + 1} failed: {str(e)}")
                if attempt == 1:
                    error_info = {
                        "success": False,
                        "error": f"Gemini API error (all attempts failed): {str(e)}",
                        "raw_response": None,
                    }
                    try:
                        if "response" in locals() and response:
                            response_text = self._extract_response_text(response)
                            error_info["raw_response"] = (
                                response_text[:1000]
                                if response_text
                                else "No text content"
                            )
                            if hasattr(response, "candidates"):
                                error_info["candidates_count"] = (
                                    len(response.candidates)
                                    if response.candidates
                                    else 0
                                )
                    except:
                        pass

                    return error_info
                continue

    def analyze_investment_data(self, document_text):
        try:
            full_prompt = self.investment_prompt + document_text
            response = self.model.generate_content(
                full_prompt, generation_config=self.generation_config
            )

            if not response.text:
                raise ValueError("No response generated from Gemini")

            investment_data = self._parse_investment_response(response.text)

            return {"success": True, "data": investment_data}

        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini API error: {str(e)}",
                "raw_response": None,
            }

    def check_investment_sufficiency(self, document_text):
        try:
            sufficiency_prompt = self._get_sufficiency_prompt() + document_text
            response = self.model.generate_content(
                sufficiency_prompt, generation_config=self.generation_config
            )

            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("No text content in Gemini response")

            sufficiency_data = self._parse_sufficiency_response(response_text)

            return {"success": True, **sufficiency_data}

        except Exception as e:
            return {"success": False, "error": f"Gemini API error: {str(e)}"}

    def aggregate_investment_responses(self, model_responses, financial_data, valuation_data, investment_data):
        """
        Use Gemini to aggregate the responses from 5 OpenRouter models into a final investment decision
        """
        try:
            # Filter successful responses
            successful_responses = [r for r in model_responses if r["success"]]

            if not successful_responses:
                return {
                    "verdict": "insufficient_data",
                    "confidence": 0,
                    "error": "No models provided valid responses",
                }

            # Build enhanced aggregation prompt for Gemini
            aggregation_prompt = f"""
You are the final investment decision aggregator using Google Gemini. You have received responses from {len(successful_responses)} AI models (from OpenRouter), each with different weights/coefficients. Your task is to produce a final normalized investment decision that takes these coefficients into account and provides realistic, well-reasoned output.

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

ALL OF THE DATA IS PROVIDED IN GEL CURRENCY

If there was no equity specified, come up with a reasonable equity percentage based on the stage of the company and the typical equity percentage for that stage.

If there was no valuation specified, come up with a reasonable valuation based on the stage of the company and the typical valuation for that stage.

RULES (strict — follow exactly):

1. **Aggregate model responses using their coefficients**: 
   - Weight each model's numerical outputs (valuations, confidence, risk scores) by their coefficient
   - For verdicts: prioritize higher-weighted models, but ensure logical consistency
   - Normalize and moderate extreme values to realistic ranges
   - Provide evidence-based rationale for why these aggregated values are appropriate

2. **Confidence per method (0–1)**: Derive a confidence for each method based on data quality and model agreement.

3. **Risk adjustment**: Compute risk_score (0–1) as average of normalized risk inputs in NEW_INFO_JSON.risk_factors.

4. **Decision rules**: Apply verdict logic based on status, data quality, risk score, and ownership thresholds.

5. **Recommended offer**: 
   - Suggest raise_amount targeting adjusted_p50
   - Calculate equity_pct = 100 × raise_amount / (pre_money + raise_amount) - ENSURE this is a realistic percentage (typically 10-25% for institutional rounds)
   - If calculated equity is unrealistic (< 1% or > 50%), adjust raise_amount to target 15-20% equity range

6. **Provenance & transparency**: Include detailed evidence and reasoning for all major decisions.

7. **Final Summary**: Provide clear rationale explaining why this aggregated decision is more reliable than individual model outputs, with specific evidence from the data and model consensus/disagreements.

8. **Investment Analysis**: Provide detailed reasoning for the investment decision:
   - why_invest: Compelling reasons why this is a good investment opportunity (be specific about business model, traction, team)
   - growth_potential: Detailed analysis of growth prospects with specific metrics and market drivers
   - market_opportunity: Size of addressable market and company's positioning
   - competitive_advantages: What makes this company unique and defensible
   - key_risks: Specific risks that could impact returns (market, execution, financial, competitive)
   - mitigation_strategies: How identified risks can be managed or reduced
   - expected_returns: Realistic return expectations based on valuation and growth trajectory
   - timeline_expectations: Expected timeline for value creation and potential exit opportunities

OUTPUT_SCHEMA (return this JSON with these keys and types):

{
  "verdict": "invest" | "consider_with_conditions" | "dont_invest" | "insufficient_data",
  "confidence": number 0-100,
  "valuation": {
    "raw": { "p25": number | null, "p50": number | null, "p75": number | null },
    "adjusted": { "p25": number | null, "p50": number | null, "p75": number | null },
    "method_breakdown": {
      "dcf": {"p25":number,"p50":number,"p75":number,"confidence":number} | null,
      "multiples": {"p25":number,"p50":number,"p75":number,"confidence":number} | null,
      "precedent": {"p25":number,"p50":number,"p75":number,"confidence":number} | null,
      "rule_of_thumb": {"p25":number,"p50":number,"p75":number,"confidence":number} | null
    }
  },
  "recommended_offer": { "raise_amount": number | null, "equity_pct": number | null, "terms": string | null },
  "cap_table_impact": { "price_per_share_pre": number | null, "new_shares": number | null, "total_shares_after": number | null, "investor_pct_after": number | null },
  "offer_assessment": { 
    "status": "attractive" | "fair" | "expensive" | "inconsistent" | "insufficient_data", 
    "details": string,
    "implied_pre_money_from_offer": number | null,
    "implied_percent_from_raise": number | null,
    "implied_amount_from_equity_pct": number | null,
    "consistency_check": "consistent" | "inconsistent" | "insufficient_data"
  },
  "risk_score": number 0-1,
  "top_evidence": [ {"title": string, "value": number | string, "source": string, "why": string} ],
  "rationale": [ string ],
  "follow_up_questions": [ string ],
  "provenance": { "internal_docs": [ string ], "external_apis": [ string ], "timestamp": string },
  "simple_summary": {
    "headline": string,
    "why": string,
    "risk_and_consistency": string,
    "next_steps": string
  },
  "aggregation_summary": {
    "models_consensus": string,
    "key_disagreements": string,
    "final_reasoning": string,
    "confidence_basis": string
  },
  "investment_analysis": {
    "why_invest": string,
    "growth_potential": string,
    "market_opportunity": string,
    "competitive_advantages": string,
    "key_risks": string,
    "mitigation_strategies": string,
    "expected_returns": string,
    "timeline_expectations": string
  }
}

ADDITIONAL INSTRUCTIONS:
- Perform arithmetic carefully and return currency numbers rounded to 2 decimal places and percentages to up to 4 decimal places.
- If you must estimate, provide the estimate with appropriate confidence and state the reason in rationale.
- Include aggregation_summary explaining how model responses were combined and why this final decision is superior.
- Ensure all numeric fields are present (use null where not computable).
- Timestamp format must be ISO 8601 UTC.
- Return ONLY the JSON structure. No explanations or markdown outside the JSON.

Now analyze the provided data and model responses, apply the coefficients appropriately, and RETURN the single JSON result that follows OUTPUT_SCHEMA.
"""

            # Generate response using Gemini
            response = self.model.generate_content(
                aggregation_prompt, generation_config=self.generation_config
            )

            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("No text content in Gemini response")

            # Parse the aggregated response
            aggregated_result = self._parse_investment_response(response_text)
            
            print(f"DEBUG: Gemini aggregation completed successfully")
            print(f"DEBUG: Final verdict: {aggregated_result.get('verdict', 'unknown')}")
            print(f"DEBUG: Final confidence: {aggregated_result.get('confidence', 0)}")
            
            return aggregated_result

        except Exception as e:
            print(f"ERROR: Gemini aggregation failed: {str(e)}")
            # Fallback: return the highest weighted successful response
            if successful_responses:
                best_response = max(successful_responses, key=lambda x: x["weight"])
                return best_response["response"]
            else:
                return {
                    "verdict": "insufficient_data",
                    "confidence": 0,
                    "error": f"Gemini aggregation error: {str(e)}",
                }

    def _parse_response(self, response_text):
        try:
            if not response_text or response_text.strip() == "":
                raise ValueError("Empty response from Gemini API")

            response_text = response_text.strip()
            json_text = self._extract_json_content(response_text)

            if not json_text:
                raise ValueError(
                    f"No valid JSON found in response. Raw response: {response_text[:200]}..."
                )
            json_text = json_text.replace("\\n", "\n").replace('\\"', '"')
            json_text = self._fix_common_json_issues(json_text)

            if not json_text.rstrip().endswith("}"):
                json_text = self._fix_truncated_json(json_text)

            parsed_data = json.loads(json_text)
            if "financial_analysis" in parsed_data:
                parsed_data["financial_analysis"] = self._convert_string_numbers(
                    parsed_data["financial_analysis"]
                )

            return parsed_data

        except json.JSONDecodeError as e:
            try:
                partial_data = self._extract_partial_data(response_text)
                if partial_data:
                    return partial_data
            except:
                pass
            raise ValueError(
                f"Failed to parse JSON response from Gemini: {str(e)}. Raw response: {response_text[:500]}..."
            )
        except Exception as e:
            raise ValueError(
                f"Response parsing error: {str(e)}. Raw response: {response_text[:500]}..."
            )

    def _extract_response_text(self, response):
        try:
            if hasattr(response, "text") and response.text:
                return response.text
        except ValueError:
            pass

        try:
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content:
                    if hasattr(candidate.content, "parts") and candidate.content.parts:
                        text_parts = []
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                text_parts.append(part.text)
                        return "".join(text_parts)
        except Exception as e:
            print(f"Error extracting response text: {e}")

        return None

    def _extract_json_content(self, response_text):
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                return response_text[start:end].strip()
        if response_text.startswith("```") and response_text.endswith("```"):
            return response_text[3:-3].strip()
        if "{" in response_text and "}" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            return response_text[start:end]
        return response_text

    def _fix_common_json_issues(self, json_text):
        import re

        json_text = re.sub(r",(\s*[}\]])", r"\1", json_text)
        json_text = re.sub(r'}(\s*),(\s*)"', r'}\2"', json_text)
        json_text = re.sub(r",,+", ",", json_text)
        json_text = re.sub(r'}(\s+)"', r'},\1"', json_text)
        json_text = re.sub(r'](\s+)"', r'],\1"', json_text)
        json_text = re.sub(r'(\d)(\s+)"', r'\1,\2"', json_text)
        json_text = re.sub(r'null(\s+)"', r'null,\1"', json_text)

        return json_text

    def _convert_string_numbers(self, data):
        if isinstance(data, dict):
            converted = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    converted[key] = self._convert_string_numbers(value)
                elif isinstance(value, str):
                    if value == "null" or value == "None" or value == "":
                        converted[key] = None
                    elif value.isdigit():
                        converted[key] = int(value)
                    elif (
                        value.replace(".", "")
                        .replace("-", "")
                        .replace(",", "")
                        .isdigit()
                    ):
                        clean_value = value.replace(",", "")
                        converted[key] = float(clean_value)
                    else:
                        converted[key] = value
                else:
                    converted[key] = value
            return converted
        return data

    def _fix_truncated_json(self, json_text):
        last_brace = json_text.rfind("}")
        if last_brace > 0:
            brace_count = 0
            for i in range(last_brace, -1, -1):
                if json_text[i] == "}":
                    brace_count += 1
                elif json_text[i] == "{":
                    brace_count -= 1
                    if brace_count == 0:
                        return json_text[: i + 1] + "}"
        return json_text

    def _extract_partial_data(self, json_text):
        try:
            if '"financial_analysis"' in json_text:
                start_idx = json_text.find('"financial_analysis"')
                brace_start = json_text.find("{", start_idx)
                if brace_start > 0:
                    brace_count = 0
                    end_idx = -1
                    for i in range(brace_start, len(json_text)):
                        if json_text[i] == "{":
                            brace_count += 1
                        elif json_text[i] == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i
                                break

                    if end_idx > 0:
                        partial_json = json_text[brace_start : end_idx + 1]
                        financial_data = json.loads(partial_json)
                        return {"financial_analysis": financial_data}
        except:
            pass
        return None

    def _generate_pdf_if_needed(self, financial_data):
        if (
            "summerized_data" not in financial_data
            or not financial_data["summerized_data"]
        ):
            return None

        pdf_filename = (
            f"financial_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        pdf_path = f"{Config.PDF_FOLDER}/{pdf_filename}"

        pdf_result = self.pdf_generator.generate_summary_pdf(
            financial_data["summerized_data"], pdf_path
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

Besides it, save all available financial data to the summerized data field, including summerized info about company, everything important, but do more focus on financial data, as it is a financial summary.

🚨 **CRITICAL: SUMMARIZED DATA MUST INCLUDE ALL YEARS FOUND** 🚨
The summarized_data field MUST include information for ALL years actually found across ALL files. If the documents contain only 2023 data, include only 2023. If they contain 2021-2024, include all 4 years. Do NOT add years that don't exist in the documents. Include historical trends, year-over-year changes, and comprehensive financial evolution across ALL available years.

Please provide the response in the following JSON structure:

{
    "summerized_data": {
    // All data including important financial data, company info etc. make more focus on financial data 
    },
  "financial_analysis": {
    "income_statement": {
      "revenue_sales": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "cogs": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "gross_profit": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found", "note": "calculated"},
      "operating_expenses": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "depreciation_amortization": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "other_operating_income_expense": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "operating_profit_ebit": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "interest_expense": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "interest_income": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "foreign_exchange_gains_losses": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "profit_before_tax_ebt": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "income_tax_expense": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "net_income": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"}
    },
    "balance_sheet": {
      "cash_equivalents": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "accounts_receivable": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "inventory": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "other_current_assets": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "ppe": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "intangible_assets": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "accounts_payable": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "short_term_debt": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "long_term_debt": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "deferred_tax_liabilities": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "shareholders_equity": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"}
    },
    "cash_flow_statement": {
      "cash_flow_from_operations": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "taxes_paid": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "interest_paid": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "capital_expenditures": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "changes_in_working_capital": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found"},
      "free_cash_flow": {"YEAR1": "number", "YEAR2": "number", "etc": "for all years found", "note": "calculated"}
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

🚨 **MANDATORY MULTI-YEAR EXTRACTION REQUIREMENTS - DO NOT IGNORE** 🚨

**CRITICAL RULE: YOU MUST EXTRACT DATA FOR ALL YEARS FOUND IN ALL FILES**

1. **SCAN ALL FILES**: The document contains MULTIPLE files separated by "--- FILE:" markers. YOU MUST analyze EVERY SINGLE FILE.

2. **EXTRACT ALL YEARS FOUND**: Do NOT limit yourself to recent years. Extract ONLY the years that actually contain data in the documents. If you find data for 2021, 2022, 2023, 2024, 2025, or ANY other years, you MUST include ALL of them in your response. If only 2023 data exists, include only 2023. If 2021-2024 exists, include all 4 years.

3. **NO CHERRY-PICKING**: Do NOT select only the "most recent" or "most complete" years. Extract EVERY year you find.

4. **HISTORICAL DATA PRIORITY**: Often older files contain 2021-2022 data and newer files contain 2023-2024 data. YOU MUST INCLUDE BOTH.

5. **VERIFICATION REQUIREMENT**: Before responding, verify you have extracted data for ALL years mentioned in ALL files.

6. **ALL THE YEARS SHOULD BE A VALID YEAR**: Check if year is valid, it should be saying 2021, not 21.

7. **APPLIES TO ALL SECTIONS**: This requirement applies to BOTH the "financial_analysis" section AND the "summarized_data" section. BOTH must include all years. 

**EXAMPLE SCENARIOS (FOLLOW THESE EXACTLY):**

**Scenario A - Multiple Years:**
- File 1: Contains 2023-2024 data → Extract 2023, 2024
- File 2: Contains 2021-2022 data → Extract 2021, 2022  
- YOUR RESPONSE: MUST include ALL years: 2021, 2022, 2023, 2024

**Scenario B - Single Year:**
- File 1: Contains only 2023 data → Extract only 2023
- YOUR RESPONSE: Include only 2023

**Scenario C - Two Years:**
- File 1: Contains 2022-2023 data → Extract 2022, 2023
- YOUR RESPONSE: Include only 2022, 2023

**CRITICAL RULE: ONLY INCLUDE YEARS THAT ACTUALLY HAVE DATA IN THE DOCUMENTS**

**FAILURE TO FOLLOW = INCORRECT RESPONSE**

If any information is not available for a specific year, use null for that field. Include extraction_notes for any items that could not be found or extracted. Be precise with numbers and focus on extracting quantitative data that would be valuable for investment analysis.

RETURN ONLY THE JSON OBJECT - NO OTHER TEXT.

⚠️ FINAL REMINDER: The document below contains MULTIPLE years across MULTIPLE files. Extract ALL years - do not limit to recent years only. ⚠️

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
                        "market_analysis": response_text,
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
                    "parse_error": str(e),
                }
            }
        except Exception as e:
            return {
                "investment_analysis": {
                    "summary": f"Error processing investment analysis: {str(e)}",
                    "recommendations": [],
                    "risk_assessment": "Processing error",
                    "opportunities": [],
                    "market_analysis": (
                        response_text if "response_text" in locals() else "No response"
                    ),
                    "error": str(e),
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

**CRITICAL INVESTMENT ASSESSMENT LOGIC:**

1. **If the business fundamentals are sound** but data is missing:
   - Rate based on data completeness (0-100%)
   - Focus on what additional data is needed
   - Provide recommendations for data gathering

2. **If the business fundamentals are flawed** (poor business model, declining metrics, insurmountable risks):
   - Set sufficiency_percentage to 0
   - In missing_data, state "INVESTMENT NOT RECOMMENDED - Business fundamentals are flawed"
   - In recommendations, explain why this is not a viable investment
   - In critical_gaps, list the fundamental business problems

Rate the overall sufficiency considering that institutional-quality investment decisions typically require 80%+ data completeness, BUT if the business itself is fundamentally flawed, return 0% regardless of data completeness.

Provide your response in this exact JSON format:

{
    "sufficiency_percentage": <number 0-100>,
    "missing_data": [
        "Specific missing data point 1 OR 'INVESTMENT NOT RECOMMENDED - Business fundamentals are flawed'",
        "Specific missing data point 2"
    ],
    "recommendations": [
        "Specific actionable recommendation 1 OR reasons why investment should be avoided",
        "Specific actionable recommendation 2"
    ],
    "critical_gaps": [
        "Critical gap 1 that prevents investment decision OR fundamental business flaw",
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
        """Parse sufficiency check response from Gemini with enhanced error handling"""
        try:
            response_text = response_text.strip()

            # Try multiple extraction methods
            json_text = None

            # Method 1: Standard JSON extraction
            json_text = self._extract_json_content(response_text)

            # Method 2: If that fails, try to find JSON boundaries more aggressively
            if not json_text or len(json_text.strip()) < 10:
                # Look for any { } pair
                start_brace = response_text.find("{")
                end_brace = response_text.rfind("}")
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    json_text = response_text[start_brace : end_brace + 1]

            if not json_text:
                # Method 3: Extract from markdown code blocks more aggressively
                import re

                # Look for any content between ``` blocks
                code_blocks = re.findall(
                    r"```(?:json)?\s*({.*?})\s*```",
                    response_text,
                    re.DOTALL | re.IGNORECASE,
                )
                if code_blocks:
                    json_text = code_blocks[0]

            if not json_text:
                # Fallback: try to extract key information manually
                return self._extract_sufficiency_manually(response_text)

            # Clean and parse JSON with enhanced cleaning
            json_text = self._clean_json_for_parsing(json_text)

            try:
                parsed_data = json.loads(json_text)
            except json.JSONDecodeError:
                # Try one more cleaning pass
                json_text = self._aggressive_json_cleaning(json_text)
                parsed_data = json.loads(json_text)

            # Ensure all required fields exist with defaults
            return {
                "sufficiency_percentage": parsed_data.get("sufficiency_percentage", 50),
                "missing_data": parsed_data.get("missing_data", []),
                "recommendations": parsed_data.get("recommendations", []),
                "critical_gaps": parsed_data.get("critical_gaps", []),
            }

        except json.JSONDecodeError as e:
            # Try to extract any valid data from partial JSON
            try:
                # Look for percentage in the raw text
                import re

                percentage_match = re.search(
                    r'"sufficiency_percentage":\s*(\d+)', response_text
                )
                percentage = int(percentage_match.group(1)) if percentage_match else 40

                # Try to extract missing data array
                missing_match = re.search(
                    r'"missing_data":\s*\[(.*?)\]', response_text, re.DOTALL
                )
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
                    "recommendations": [
                        "Response was partially parsed due to formatting issues"
                    ],
                    "critical_gaps": ["Partial data extraction performed"],
                }
            except:
                return {
                    "sufficiency_percentage": 40,
                    "missing_data": ["JSON parsing error in response"],
                    "recommendations": [
                        f"Raw response preview: {response_text[:300]}..."
                    ],
                    "critical_gaps": ["Model response format error"],
                }
        except Exception as e:
            return {
                "sufficiency_percentage": 30,
                "missing_data": [f"Error parsing response: {str(e)}"],
                "recommendations": ["Please try again"],
                "critical_gaps": ["System error occurred"],
            }

    def _clean_json_for_parsing(self, json_text):
        """Enhanced JSON cleaning for parsing"""
        # Remove any leading/trailing whitespace
        json_text = json_text.strip()

        # Remove any markdown formatting
        if json_text.startswith("```") and json_text.endswith("```"):
            json_text = json_text[3:-3].strip()

        if json_text.startswith("json"):
            json_text = json_text[4:].strip()

        # Apply existing cleaning
        json_text = self._fix_common_json_issues(json_text)

        return json_text

    def _aggressive_json_cleaning(self, json_text):
        """More aggressive JSON cleaning as last resort"""
        import re

        # Remove any text before the first {
        first_brace = json_text.find("{")
        if first_brace > 0:
            json_text = json_text[first_brace:]

        # Remove any text after the last }
        last_brace = json_text.rfind("}")
        if last_brace != -1:
            json_text = json_text[: last_brace + 1]

        # Fix common issues
        json_text = re.sub(r",(\s*[}\]])", r"\1", json_text)  # Remove trailing commas
        json_text = re.sub(
            r'([}\]])(\s*)(["\w])', r"\1,\2\3", json_text
        )  # Add missing commas

        return json_text

    def _extract_sufficiency_manually(self, response_text):
        """Manual extraction when JSON parsing completely fails"""
        import re

        # Try to extract percentage
        percentage_patterns = [
            r'sufficiency_percentage["\s]*:\s*(\d+)',
            r'percentage["\s]*:\s*(\d+)',
            r"(\d+)%",
            r"(\d+)\s*percent",
        ]

        percentage = 40  # Default
        for pattern in percentage_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                percentage = int(match.group(1))
                break

        # Detect investment negative signals
        negative_signals = [
            "shit",
            "terrible",
            "awful",
            "horrible",
            "not viable",
            "fundamentally flawed",
            "should not invest",
            "avoid investment",
            "not recommended",
            "poor business model",
            "declining",
            "unsustainable",
            "high risk",
            "unprofitable",
        ]

        is_negative = any(
            signal in response_text.lower() for signal in negative_signals
        )

        if is_negative or percentage == 0:
            return {
                "sufficiency_percentage": 0,
                "missing_data": [
                    "INVESTMENT NOT RECOMMENDED - Business fundamentals are flawed"
                ],
                "recommendations": [
                    "Avoid this investment opportunity due to fundamental business issues"
                ],
                "critical_gaps": [
                    "Poor business model or fundamentally flawed investment opportunity"
                ],
            }

        return {
            "sufficiency_percentage": percentage,
            "missing_data": [
                "Complete response could not be parsed - manual review recommended"
            ],
            "recommendations": ["Request additional data and re-run analysis"],
            "critical_gaps": ["Response parsing incomplete"],
        }
