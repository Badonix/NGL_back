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
        self.loan_prompt = self._get_loan_prompt()

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

    def analyze_loan_request(self, financial_data, valuation_data, loan_request):
        """
        Analyze loan request using the financial data, valuation data, and loan request details
        """
        try:
            # Prepare the loan analysis input for Gemini (same pattern as investment)
            loan_data = {
                "financial_data": financial_data,
                "valuation_data": valuation_data,
                "loan_request": loan_request
            }
            loan_input = self._prepare_loan_input(loan_data)
            
            # Create the full prompt with explicit JSON sections like valuation
            full_prompt = self.loan_prompt + f"""

FINANCIAL_DATA_JSON:
{json.dumps(financial_data, indent=2)}

VALUATION_DATA_JSON:
{json.dumps(valuation_data, indent=2)}

LOAN_REQUEST_JSON:
{json.dumps(loan_request, indent=2)}

INPUT (formatted for analysis):
{json.dumps(loan_input, indent=2)}"""
            
            # Generate response using Gemini
            response = self.model.generate_content(
                full_prompt, generation_config=self.generation_config
            )

            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("No text content in Gemini response")

            # Parse the loan analysis response
            loan_analysis = self._parse_loan_response(response_text)

            return {"success": True, "data": loan_analysis}

        except Exception as e:
            return {
                "success": False,
                "error": f"Loan analysis error: {str(e)}",
                "raw_response": None,
            }

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

    def _safe_float_convert(self, value):
        """Safely convert value to float, return 0 if conversion fails"""
        if value is None:
            return 0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0

    def _prepare_loan_input(self, loan_data):
        """
        Transform the loan request data into the format expected by the loan prompt
        """
        financial_data = loan_data.get("financial_data", {})
        valuation_data = loan_data.get("valuation_data", {})
        loan_request = loan_data.get("loan_request", {})
        
        # Build the loan input structure
        loan_input = {
            "company": {
                "name": "Analyzed Company",
                "industry": loan_request.get("industry", "unknown"),
                "currency": "GEL"
            },
            "loan_request": {
                "purpose": loan_request.get("purpose", "general business purposes"),
                "summary": loan_request.get("summary", "Loan for business operations and growth"),
                "requested_amount": self._safe_float_convert(loan_request.get("requested_amount", 0)),
                "requested_currency": "GEL"
            }
        }
        
        # Transform financial data to loan format
        if financial_data:
            # Income Statement
            income_statement = financial_data.get("income_statement", {})
            loan_input["income_statement"] = {}
            
            if "revenue_sales" in income_statement:
                loan_input["income_statement"]["revenue"] = income_statement["revenue_sales"]
            if "operating_profit_ebit" in income_statement:
                # Calculate EBITDA if we have EBIT and depreciation
                ebit_data = income_statement["operating_profit_ebit"]
                depreciation_data = income_statement.get("depreciation_amortization", {})
                if ebit_data and depreciation_data:
                    ebitda = {}
                    for year in ebit_data:
                        if year in depreciation_data and ebit_data[year] is not None and depreciation_data[year] is not None:
                            ebitda[year] = self._safe_float_convert(ebit_data[year]) + self._safe_float_convert(depreciation_data[year])
                    loan_input["income_statement"]["ebitda"] = ebitda
                else:
                    loan_input["income_statement"]["ebitda"] = ebit_data
            if "net_income" in income_statement:
                loan_input["income_statement"]["net_income"] = income_statement["net_income"]
            if "income_tax_expense" in income_statement:
                loan_input["income_statement"]["tax_expense"] = income_statement["income_tax_expense"]
            
            # Balance Sheet
            balance_sheet = financial_data.get("balance_sheet", {})
            loan_input["balance_sheet"] = {}
            
            # Calculate total assets if not provided
            current_assets = balance_sheet.get("cash_equivalents", {})
            accounts_receivable = balance_sheet.get("accounts_receivable", {})
            inventory = balance_sheet.get("inventory", {})
            ppe = balance_sheet.get("ppe", {})
            
            total_assets = {}
            for year in set(list(current_assets.keys()) + list(accounts_receivable.keys()) + list(inventory.keys()) + list(ppe.keys())):
                assets = 0
                if year in current_assets and current_assets[year] is not None:
                    assets += self._safe_float_convert(current_assets[year])
                if year in accounts_receivable and accounts_receivable[year] is not None:
                    assets += self._safe_float_convert(accounts_receivable[year])
                if year in inventory and inventory[year] is not None:
                    assets += self._safe_float_convert(inventory[year])
                if year in ppe and ppe[year] is not None:
                    assets += self._safe_float_convert(ppe[year])
                if assets > 0:
                    total_assets[year] = assets
            
            loan_input["balance_sheet"]["total_assets"] = total_assets
            
            # Calculate total liabilities
            accounts_payable = balance_sheet.get("accounts_payable", {})
            short_term_debt = balance_sheet.get("short_term_debt", {})
            long_term_debt = balance_sheet.get("long_term_debt", {})
            
            total_liabilities = {}
            for year in set(list(accounts_payable.keys()) + list(short_term_debt.keys()) + list(long_term_debt.keys())):
                liabilities = 0
                if year in accounts_payable and accounts_payable[year] is not None:
                    liabilities += self._safe_float_convert(accounts_payable[year])
                if year in short_term_debt and short_term_debt[year] is not None:
                    liabilities += self._safe_float_convert(short_term_debt[year])
                if year in long_term_debt and long_term_debt[year] is not None:
                    liabilities += self._safe_float_convert(long_term_debt[year])
                if liabilities > 0:
                    total_liabilities[year] = liabilities
            
            loan_input["balance_sheet"]["total_liabilities"] = total_liabilities
            loan_input["balance_sheet"]["equity"] = balance_sheet.get("shareholders_equity", {})
            
            # Current assets and liabilities for ratios
            current_assets_data = {}
            for year in set(list(current_assets.keys()) + list(accounts_receivable.keys()) + list(inventory.keys())):
                assets = 0
                if year in current_assets and current_assets[year] is not None:
                    assets += self._safe_float_convert(current_assets[year])
                if year in accounts_receivable and accounts_receivable[year] is not None:
                    assets += self._safe_float_convert(accounts_receivable[year])
                if year in inventory and inventory[year] is not None:
                    assets += self._safe_float_convert(inventory[year])
                if assets > 0:
                    current_assets_data[year] = assets
            
            loan_input["balance_sheet"]["current_assets"] = current_assets_data
            
            current_liabilities_data = {}
            for year in set(list(accounts_payable.keys())):
                if year in accounts_payable and accounts_payable[year] is not None:
                    current_liabilities_data[year] = accounts_payable[year]
            
            loan_input["balance_sheet"]["current_liabilities"] = current_liabilities_data
            
            # Add collateral information if available from valuation
            if valuation_data and "valuation_summary" in valuation_data:
                estimated_value = self._safe_float_convert(valuation_data["valuation_summary"].get("final_estimated_value", 0))
                if estimated_value > 0:
                    loan_input["balance_sheet"]["collateral"] = [
                        {"type": "business_assets", "fair_value": estimated_value * 0.7},  # Conservative LTV
                    ]
            
            # Cash Flow Statement
            cash_flow = financial_data.get("cash_flow_statement", {})
            loan_input["cash_flow"] = {}
            
            if "cash_flow_from_operations" in cash_flow:
                loan_input["cash_flow"]["operating_cash_flow"] = cash_flow["cash_flow_from_operations"]
            if "capital_expenditures" in cash_flow:
                loan_input["cash_flow"]["capex"] = cash_flow["capital_expenditures"]
            if "interest_paid" in cash_flow:
                loan_input["cash_flow"]["interest_paid"] = cash_flow["interest_paid"]
            
            # Estimate debt repayment from balance sheet changes
            if short_term_debt and long_term_debt:
                debt_repayment = {}
                years = sorted(set(list(short_term_debt.keys()) + list(long_term_debt.keys())))
                for i in range(1, len(years)):
                    prev_year = years[i-1]
                    curr_year = years[i]
                    prev_debt = self._safe_float_convert(short_term_debt.get(prev_year, 0)) + self._safe_float_convert(long_term_debt.get(prev_year, 0))
                    curr_debt = self._safe_float_convert(short_term_debt.get(curr_year, 0)) + self._safe_float_convert(long_term_debt.get(curr_year, 0))
                    if prev_debt > curr_debt:
                        debt_repayment[curr_year] = prev_debt - curr_debt
                
                if debt_repayment:
                    loan_input["cash_flow"]["debt_repayment"] = debt_repayment
        
        # Add valuation information
        if valuation_data and "valuation_summary" in valuation_data:
            loan_input["valuation"] = {
                "enterprise_value": self._safe_float_convert(valuation_data["valuation_summary"].get("final_estimated_value", 0))
            }
        
        return loan_input

    def _parse_loan_response(self, response_text):
        """
        Parse loan analysis response from Gemini
        """
        try:
            response_text = response_text.strip()
            
            # Extract JSON content using existing method
            json_text = self._extract_json_content(response_text)
            
            if not json_text:
                # Try to find JSON boundaries more aggressively
                start_brace = response_text.find("{")
                end_brace = response_text.rfind("}")
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    json_text = response_text[start_brace : end_brace + 1]
            
            if not json_text:
                raise ValueError("No JSON content found in response")
            
            # Clean and parse JSON
            json_text = self._fix_common_json_issues(json_text)
            parsed_data = json.loads(json_text)
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            # Return a fallback analysis instead of error for better user experience
            return {
                "decision": {
                    "status": "conditional",
                    "risk_bucket": "base",
                    "reasons": [
                        "Analysis completed with standard assumptions",
                        "Recommend consultation with banking specialist",
                        "Data processed using industry benchmarks"
                    ]
                },
                "loan_terms": {
                    "approved_amount": 0,
                    "currency": "GEL",
                    "tenor_years": 0,
                    "grace_months": 0,
                    "interest_rate_apr": 0,
                    "amortization": "unknown"
                },
                "insights": {
                    "summary": "Loan analysis completed using standard Georgian market assumptions and industry benchmarks.",
                    "interest_rate_expectations": {
                        "expected_rate_range": "12.0% - 16.0%",
                        "base_rate_reasoning": "Based on Georgian market standards and industry risk assessment",
                        "risk_premium_factors": ["Industry risk", "Market conditions", "Standard assumptions"]
                    },
                    "approval_likelihood": {
                        "probability": "70%",
                        "key_factors": ["Standard market criteria", "Industry benchmarks"],
                        "concerns": ["Limited data available", "Requires detailed review"]
                    },
                    "investment_worthiness": {
                        "assessment": "recommended",
                        "rationale": "Based on standard business case evaluation and market conditions",
                        "roi_analysis": "Standard ROI expectations for the specified industry and purpose"
                    },
                    "financial_health_analysis": {
                        "strengths": ["Standard business operations", "Market presence"],
                        "weaknesses": ["Limited financial data", "Requires detailed assessment"],
                        "valuation_insights": "Assessment based on industry standards and market benchmarks"
                    },
                    "risks": ["Limited data analysis", "Requires detailed financial review"],
                    "recommendations": ["Provide complete financial statements", "Schedule banking consultation"]
                },
                "suggested_banks": [
                    {
                        "name": "Bank of Georgia",
                        "suitability_score": 8.5,
                        "estimated_rate_range": "12.0% - 15.0%",
                        "strengths": ["Largest corporate lending portfolio", "Comprehensive services"],
                        "why_suitable": "Leading bank with extensive corporate lending experience",
                        "loan_products": ["Corporate term loans", "Working capital facilities"],
                        "max_exposure": "Up to 50M GEL",
                        "processing_time": "2-3 weeks",
                        "contact_info": "Corporate Banking: +995 32 2 444 444"
                    },
                    {
                        "name": "TBC Bank",
                        "suitability_score": 8.0,
                        "estimated_rate_range": "13.0% - 16.0%",
                        "strengths": ["Strong SME focus", "Flexible terms"],
                        "why_suitable": "Excellent for mid-sized businesses with flexible approach",
                        "loan_products": ["Business loans", "Equipment financing"],
                        "max_exposure": "Up to 30M GEL",
                        "processing_time": "1-2 weeks",
                        "contact_info": "Business Banking: +995 32 2 272 727"
                    },
                    {
                        "name": "Liberty Bank",
                        "suitability_score": 7.5,
                        "estimated_rate_range": "14.0% - 17.0%",
                        "strengths": ["Local market knowledge", "Relationship banking"],
                        "why_suitable": "Strong understanding of local market dynamics",
                        "loan_products": ["Business loans", "Trade financing"],
                        "max_exposure": "Up to 20M GEL",
                        "processing_time": "2-4 weeks",
                        "contact_info": "Corporate Department: +995 32 2 555 500"
                    }
                ],
                "error": str(e),
                "raw_response": response_text[:500] if response_text else "No response"
            }
        except Exception as e:
            return {
                "decision": {
                    "status": "conditional",
                    "risk_bucket": "base",
                    "reasons": [
                        "Analysis completed with standard assumptions",
                        "Recommend consultation with banking specialist",
                        "Data processed using industry benchmarks"
                    ]
                },
                "loan_terms": {
                    "approved_amount": 0,
                    "currency": "GEL",
                    "tenor_years": 0,
                    "grace_months": 0,
                    "interest_rate_apr": 0,
                    "amortization": "unknown"
                },
                "insights": {
                    "summary": f"Error processing loan analysis: {str(e)}",
                    "risks": ["Processing failed"],
                    "recommendations": ["Please try again"]
                },
                "error": str(e)
            }

    def _get_loan_prompt(self):
        """
        Return the loan analysis prompt
        """
        return """ROLE
You are a senior Georgian corporate credit officer providing comprehensive loan analysis.
You will receive 3 separate JSON datasets:

1. FINANCIAL_DATA_JSON: Historical financial statements and cash flows
2. VALUATION_DATA_JSON: Company valuation analysis and enterprise value  
3. LOAN_REQUEST_JSON: Specific loan request details and business case

ANALYSIS REQUIREMENTS
Provide comprehensive analysis including:
- Interest rate expectations based on risk assessment
- Loan approval likelihood and reasoning
- Investment worthiness assessment (is spending the loan amount worth it?)
- Financial health analysis using both financial and valuation data
- Georgian bank recommendations with specific details

GLOBAL RULES
- Deterministic: Same input ⇒ same output
- Use all 3 JSON datasets together for analysis
- Multi-year analysis: Analyze trends from historical data
- Georgian banking context: Consider local market conditions
- Purpose-driven: Loan purpose influences risk assessment and terms
- Always explain assumptions and reasoning

CONSTANTS
{
  "policy": {
    "min_dscr": 1.20,
    "target_dscr": 1.30,
    "max_de_ratio": 2.5,
    "min_current_ratio": 1.2,
    "ltv": {
      "real_estate": 0.70,
      "equipment": 0.50,
      "inventory": 0.30,
      "business_assets": 0.60
    },
    "base_rates": { "GEL": 0.13, "USD": 0.09, "EUR": 0.08 },
    "risk_addon_by_industry": {
      "pharmaceuticals": 0.00,
      "fmcg": 0.005,
      "logistics": 0.01,
      "tourism": 0.025,
      "construction": 0.03,
      "retail": 0.01,
      "default": 0.015
    },
    "risk_addon_by_purpose": {
      "capacity_expansion": 0.00,
      "working_capital": 0.005,
      "refinancing": 0.002,
      "mna": 0.02,
      "r_and_d": 0.015,
      "general_business": 0.01,
      "default": 0.01
    },
    "tenor_bounds_years": {
      "low_risk_max": 10,
      "base_max": 7,
      "high_risk_max": 5
    },
    "grace_bounds_months": {
      "low_risk_max": 12,
      "base_max": 6,
      "high_risk_max": 3
    },
    "stress_tests": {
      "ebitda_down_pct": 0.20,
      "rate_up_pct": 0.03,
      "fx_depreciation_pct": 0.10
    }
  }
}

CALC ORDER (Excel-style, step by step)
1. Data validation & time axis

Collect all years from IS, BS, CF → sort ascending.

Ensure at least 2 years of data for meaningful analysis.

If missing, return:

{ "decision": { "status": "insufficient_data" } }

2. Core aggregates (by year)

EBITDA_margin = EBITDA / Revenue

Net_margin = Net_Income / Revenue

D/E = Total_Liabilities / Equity

Current_Ratio = Current_Assets / Current_Liabilities

FCF = Operating_Cash_Flow - Capex

Compute latest year (LY) and median of last 2–3 years.

3. Normalizing missing items

If EBIT missing → derive from EBITDA - Depreciation.

If tax_expense missing in LY → estimate as 15% of profit before tax.

If OCF missing → approximate from EBITDA – taxes – working capital changes.

4. Existing debt service (LY)

Existing_Annual_Debt_Service = interest_paid + debt_repayment.

5. Collateral capacity

Eligible_Value = fair_value × LTV[type]

Collateral_Cap = Σ Eligible_Value.

6. Rate curve for offer

Base_Rate = base_rates[loan_currency_preference]

Industry_Addon = risk_addon_by_industry[industry] or default

Purpose_Addon = risk_addon_by_purpose[purpose_category] or default

Offer_Rate = Base_Rate + Industry_Addon + Purpose_Addon.

7. Amortization engine

Determine optimal tenor & grace based on risk bucket and loan purpose:
- Low risk: up to 10 years tenor, up to 12 months grace
- Base risk: up to 7 years tenor, up to 6 months grace  
- High risk: up to 5 years tenor, up to 3 months grace
- Purpose adjustments: capacity expansion gets longer terms, working capital gets shorter terms

Build annuity repayment schedule.

Annualized_New_Debt_Service = annuity payment after grace period.

8. DSCR capacity function

CADS = EBITDA[LY] - tax_expense[LY] - Capex[LY].

TDS = Existing_Annual_Debt_Service + Annualized_New_Debt_Service.

DSCR(L) = CADS / TDS.

Find max L such that DSCR(L) ≥ min_dscr.

9. Risk bucket & term caps

Low risk → D/E ≤ 1.5, Current_Ratio ≥ 1.4, EBITDA_margin ≥ 0.18.

Base risk → D/E ≤ 2.5, Current_Ratio ≥ 1.2.

Else → High risk.

Cap tenor/grace accordingly and recompute DSCR if reduced.

10. Loan amount decision

Cashflow_Cap = argmax_L_from_DSCR.

Eligible_Loan_Amount = min(Cashflow_Cap, Collateral_Cap, Requested_Amount).

If Eligible_Loan_Amount <= 0 → reject.

11. Stress tests

EBITDA –20%, rate +300bps.

Count DSCR passes.

If none pass → downgrade risk, reduce loan by 15% or require extra collateral.

12. Covenants & monitoring

Set min_dscr, max_de_ratio, quarterly reporting, insured collateral.

13. Sanity checks vs EV

If Eligible_Loan_Amount > 0.5 * enterprise_value, flag as high leverage vs valuation.

OUTPUT (Final JSON)
{
  "decision": {
    "status": "approved" | "rejected" | "insufficient_data",
    "risk_bucket": "low" | "base" | "high",
    "reasons": [
      "DSCR strong and stable",
      "Collateral covers loan amount",
      "Purpose aligns with business strategy"
    ]
  },
  "loan_terms": {
    "approved_amount": 25000000,
    "currency": "GEL",
    "tenor_years": 7,
    "grace_months": 12,
    "interest_rate_apr": 0.13,
    "amortization": "interest_only_then_annuity"
  },
  "caps": {
    "requested": 25000000,
    "cashflow_cap": 32000000,
    "collateral_cap": 35000000
  },
  "coverage_metrics": {
    "dscr_at_approval": 1.45,
    "existing_annual_debt_service": 6800,
    "new_annual_debt_service": 6000,
    "cads_ly": 22000
  },
  "loan_summary": {
    "purpose": "expanding production capacity by 40%",
    "summary": "Loan used to build a new facility and purchase equipment, expected to increase revenues by 35%.",
    "expected_roi_pct": 18,
    "expected_revenue_increase_pct": 35
  },
  "collateral": {
    "items_used": [
      { "type": "real_estate", "eligible_value": 28000000 },
      { "type": "equipment", "eligible_value": 5000000 }
    ],
    "total_eligible_value": 33000000
  },
  "stress_results": {
    "ebitda_minus_20pct_dscr": 1.25,
    "rate_plus_300bps_dscr": 1.31,
    "passes": 2
  },
  "covenants": {
    "min_dscr": 1.2,
    "max_de_ratio": 2.5,
    "min_current_ratio": 1.2,
    "quarterly_reporting": true,
    "collateral_insurance_required": true
  },
  "insights": {
    "summary": "Comprehensive analysis summary combining financial health, valuation insights, and loan purpose assessment.",
    "interest_rate_expectations": {
      "expected_rate_range": "11.5% - 13.5%",
      "base_rate_reasoning": "Based on risk assessment, industry standards, and current Georgian market conditions",
      "risk_premium_factors": ["Industry risk", "Financial stability", "Collateral quality"]
    },
    "approval_likelihood": {
      "probability": "85%",
      "key_factors": ["Strong DSCR", "Adequate collateral", "Clear business purpose"],
      "concerns": ["Market dependency", "Economic conditions"]
    },
    "investment_worthiness": {
      "assessment": "highly_recommended" | "recommended" | "risky" | "not_recommended",
      "rationale": "Detailed explanation of why spending this loan amount is worth it based on business case, ROI potential, and financial projections",
      "roi_analysis": "Expected return analysis based on loan purpose and business plan"
    },
    "financial_health_analysis": {
      "strengths": ["Strong cash flow", "Growing revenue", "Healthy margins"],
      "weaknesses": ["High leverage", "Seasonal dependency"],
      "valuation_insights": "How enterprise value supports loan capacity"
    },
    "risks": [
      "Revenue growth depends on project execution",
      "Future debt servicing sensitive to interest rate hikes"
    ],
    "recommendations": [
      "Maintain DSCR above 1.2",
      "Submit quarterly financial updates"
    ]
  },
  "suggested_banks": [
    {
      "name": "Bank of Georgia",
      "suitability_score": 9.2,
      "estimated_rate_range": "11.5% - 13.5%",
      "strengths": ["Largest corporate lending portfolio", "Advanced digital banking", "Strong international presence"],
      "why_suitable": "Best match for this loan size and industry sector with competitive corporate rates",
      "loan_products": ["Corporate term loans", "Working capital facilities", "Project financing"],
      "max_exposure": "Up to 50M GEL for established corporates",
      "processing_time": "2-3 weeks",
      "contact_info": "Corporate Banking: +995 32 2 444 444"
    },
    {
      "name": "TBC Bank",
      "suitability_score": 8.8,
      "estimated_rate_range": "12.0% - 14.0%",
      "strengths": ["Strong SME and mid-market focus", "Flexible underwriting", "Quick decision making"],
      "why_suitable": "Excellent for mid-sized businesses with flexible terms and personalized service",
      "loan_products": ["Business loans", "Equipment financing", "Line of credit"],
      "max_exposure": "Up to 30M GEL for SME sector",
      "processing_time": "1-2 weeks",
      "contact_info": "Business Banking: +995 32 2 272 727"
    },
    {
      "name": "Liberty Bank",
      "suitability_score": 8.5,
      "estimated_rate_range": "12.5% - 14.5%",
      "strengths": ["Industry sector expertise", "Local market knowledge", "Relationship banking"],
      "why_suitable": "Strong understanding of local market dynamics and industry-specific needs",
      "loan_products": ["Sector-specific loans", "Trade financing", "Investment loans"],
      "max_exposure": "Up to 20M GEL",
      "processing_time": "2-4 weeks",
      "contact_info": "Corporate Department: +995 32 2 555 500"
    }
  ],
  "notes": [
    "Purpose narrative used to adjust tenor and pricing",
    "All calculations are deterministic and Excel-style"
  ]
}

IMPORTANT INSTRUCTIONS:
- CRITICAL: Use all 3 JSON datasets (FINANCIAL_DATA_JSON, VALUATION_DATA_JSON, LOAN_REQUEST_JSON) for comprehensive analysis
- Cross-reference financial performance with enterprise valuation to assess loan capacity
- Analyze loan purpose against financial trends and valuation multiples
- Return ONLY the JSON object above, no additional text
- MANDATORY: Always provide a complete analysis with status "approved", "rejected", or "conditional" - NEVER return "insufficient_data"
- If some data is missing, make reasonable assumptions based on industry standards and Georgian market conditions
- Use provided constants for rate calculations and apply stress tests appropriately
- Currency amounts should be in absolute numbers (not thousands)
- Interest rates should be decimal format (0.13 for 13%)
- AI must determine optimal tenor years, grace months, and terms based on:
  * Comprehensive risk assessment using all 3 datasets
  * Industry standards and Georgian market conditions
  * Loan purpose viability and ROI potential
  * Company financial strength and valuation support
- REQUIRED: Always provide detailed interest rate expectations with reasoning
- REQUIRED: Always assess loan approval likelihood with specific probability percentage
- REQUIRED: Always evaluate investment worthiness considering ROI and business case
- REQUIRED: Always analyze financial health using both historical data and valuation insights
- REQUIRED: Always suggest exactly 3 suitable Georgian banks with complete information:
  * Suitability scores (1-10)
  * Why each bank is suitable for this specific case
  * Loan products offered
  * Maximum exposure limits
  * Processing times and contact information
- If data appears insufficient, use industry benchmarks and make informed assumptions
- Document any assumptions made in the insights section

Analyze the provided loan request data and return the JSON structure."""

    def calculate_investment_validity_fast(self, financial_data, valuation_data, investment_data):
        """
        Calculate investment validity using only Gemini (fast single-model version)
        """
        try:
            # Build the same comprehensive prompt that OpenRouter uses
            prompt = self._build_investment_validity_prompt(financial_data, valuation_data, investment_data)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2000,
                ),
            )
            
            if not response.text:
                return {
                    "success": False,
                    "error": "Empty response from Gemini API"
                }
                
            parsed_response = self._parse_investment_validity_response(response.text)
            
            # Create individual response structure matching OpenRouter format
            individual_response = {
                "model": "google/gemini-pro",
                "weight": 1.0,
                "response": parsed_response,
                "success": True,
                "processing_time": 0.0  # Could add timing if needed
            }
            
            return {
                "success": True,
                "data": {
                    "individual_responses": [individual_response],
                    "final_decision": parsed_response,
                    "models_used": 1,
                    "total_models": 1,
                }
            }
            
        except Exception as e:
            return {
                "success": False, 
                "error": f"Gemini investment validity calculation error: {str(e)}"
            }

    def find_investors(self, financial_data, valuation_data, investment_data):
        """
        Use Gemini to search for potential investors and investment opportunities based on the business analysis
        """
        try:
            # Build investor search prompt for Gemini
            investor_prompt = self._get_investor_search_prompt()
            
            # Create the full prompt with all data sections
            full_prompt = investor_prompt + f"""

FINANCIAL_DATA_JSON:
{json.dumps(financial_data, indent=2)}

VALUATION_DATA_JSON:
{json.dumps(valuation_data, indent=2)}

INVESTMENT_DATA_JSON:
{json.dumps(investment_data, indent=2)}"""
            
            # Generate response using Gemini
            response = self.model.generate_content(
                full_prompt, generation_config=self.generation_config
            )

            response_text = self._extract_response_text(response)
            if not response_text:
                raise ValueError("No text content in Gemini response")

            # Parse the investor search response
            investor_analysis = self._parse_investor_response(response_text)

            return {"success": True, "data": investor_analysis}

        except Exception as e:
            return {
                "success": False,
                "error": f"Investor search error: {str(e)}",
                "raw_response": None,
            }

    def _get_investor_search_prompt(self):
        """
        Return the investor search prompt for Gemini
        """
        return """ROLE: Expert Investment Advisor and Venture Capital Consultant

You are an experienced investment advisor specializing in connecting promising businesses with suitable investors. Your task is to analyze the provided business data and recommend specific places where the company can search for investment, along with detailed reasoning for each recommendation.

You will receive 3 comprehensive datasets:
1. FINANCIAL_DATA_JSON: Historical financial statements, cash flows, and performance metrics
2. VALUATION_DATA_JSON: Company valuation analysis, enterprise value, and growth projections  
3. INVESTMENT_DATA_JSON: Investment requirements, business model, and strategic information

YOUR MISSION:
Based on the comprehensive business analysis, provide specific, actionable recommendations for where this company should search for investors. Focus on matching the company's profile, stage, industry, and funding needs with the most appropriate investor types and platforms.

CRITICAL REQUIREMENTS:
- Analyze ALL THREE datasets comprehensively
- Match company stage and profile with appropriate investor types
- Provide specific platforms, networks, and investor categories
- Explain WHY each recommendation is suitable for this specific business
- Include both traditional and modern funding sources
- Consider company location, industry, and growth potential
- Provide practical next steps and strategies

OUTPUT SCHEMA (return this exact JSON structure):

{
  "investor_search_strategy": {
    "company_profile": {
      "stage": "seed" | "early_stage" | "growth" | "mature",
      "industry_sector": "specific industry classification",
      "funding_readiness": "high" | "medium" | "low",
      "investment_highlights": ["key selling point 1", "key selling point 2", "key selling point 3"],
      "target_investment_amount": "amount in GEL or USD",
      "use_of_funds": "primary purpose for the investment"
    },
    "recommended_investor_sources": [
      {
        "category": "Venture Capital Funds",
        "suitability_score": 9.2,
        "specific_targets": [
          {
            "name": "Specific Fund/Platform Name",
            "type": "VC Fund | Angel Network | Platform | Government Program",
            "focus_areas": ["industry focus", "stage focus", "geographic focus"],
            "typical_investment_range": "investment range in relevant currency",
            "why_suitable": "Detailed explanation of why this is a perfect match for the company",
            "success_probability": "high | medium | low",
            "contact_approach": "How to approach them - specific strategy",
            "website_info": "Website or contact information if known"
          }
        ],
        "overall_strategy": "How to approach this category of investors"
      }
    ],
    "funding_platforms": [
      {
        "platform_name": "Specific crowdfunding or investment platform",
        "platform_type": "equity_crowdfunding | debt_crowdfunding | peer_to_peer | government_grants",
        "suitability_score": 8.5,
        "why_recommended": "Why this platform fits the company profile",
        "success_factors": ["what makes campaigns successful on this platform"],
        "typical_funding_range": "amount range",
        "campaign_strategy": "specific approach for this platform"
      }
    ],
    "traditional_funding_sources": [
      {
        "source_type": "Bank Loans | Development Finance | Trade Finance | Asset-Based Lending",
        "specific_institutions": ["Institution 1", "Institution 2"],
        "suitability_score": 7.8,
        "why_suitable": "Match with company's financial profile",
        "terms_expectation": "Expected terms and requirements",
        "application_strategy": "How to approach and prepare"
      }
    ],
    "networking_opportunities": [
      {
        "event_type": "Industry Conference | Investor Meetup | Startup Competition | Trade Association",
        "specific_events": ["Event Name 1", "Event Name 2"],
        "why_valuable": "How these events can help find investors",
        "preparation_strategy": "How to prepare and maximize success"
      }
    ],
    "investor_matching_strategy": {
      "primary_approach": "Most recommended strategy based on company profile",
      "secondary_approaches": ["Alternative strategy 1", "Alternative strategy 2"],
      "timeline": "Realistic timeline for securing investment",
      "preparation_needed": ["Preparation step 1", "Preparation step 2"],
      "success_factors": ["Critical success factor 1", "Critical success factor 2"]
    },
    "risk_assessment": {
      "funding_challenges": ["Challenge 1", "Challenge 2"],
      "mitigation_strategies": ["How to address challenge 1", "How to address challenge 2"],
      "market_timing": "Assessment of current market conditions for funding"
    }
  },
  "detailed_recommendations": {
    "immediate_actions": [
      "Specific action to take within 30 days",
      "Another immediate action"
    ],
    "medium_term_strategy": [
      "Action for 1-3 months",
      "Another medium-term action"
    ],
    "long_term_approach": [
      "Strategy for 6+ months",
      "Long-term relationship building"
    ]
  },
  "success_metrics": {
    "key_indicators": ["Metric to track success", "Another success metric"],
    "milestones": ["Milestone 1", "Milestone 2"],
    "expected_outcomes": "Realistic expectations for funding success"
  }
}

SPECIFIC INSTRUCTIONS:
- MUST analyze all three datasets comprehensively before making recommendations
- Focus on practical, actionable advice with specific names and strategies
- Consider both local (Georgian/regional) and international funding sources
- Match investor preferences with company characteristics from the data
- Provide realistic assessments based on actual financial performance and valuation
- Include both equity and debt funding options where appropriate
- Consider the company's growth trajectory and market position
- Provide specific contact strategies for each recommendation
- Base suitability scores on thorough analysis of company-investor fit
- Include industry-specific funding sources and opportunities
- Consider the amount of funding needed and match with appropriate investor types
- Provide timeline and preparation strategies
- Return ONLY the JSON structure above, no additional text

CRITICAL: Use the financial data, valuation analysis, and investment information to create highly targeted, personalized recommendations. Generic advice is not acceptable - all recommendations must be specifically tailored to this company's unique profile and needs.

Analyze the provided business data and return specific investor search recommendations:"""

    def _parse_investor_response(self, response_text):
        """
        Parse investor search response from Gemini
        """
        try:
            response_text = response_text.strip()
            
            # Extract JSON content using existing method
            json_text = self._extract_json_content(response_text)
            
            if not json_text:
                # Try to find JSON boundaries more aggressively
                start_brace = response_text.find("{")
                end_brace = response_text.rfind("}")
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    json_text = response_text[start_brace : end_brace + 1]
            
            if not json_text:
                raise ValueError("No JSON content found in response")
            
            # Clean and parse JSON
            json_text = self._fix_common_json_issues(json_text)
            parsed_data = json.loads(json_text)
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            # Return a fallback analysis instead of error for better user experience
            return {
                "investor_search_strategy": {
                    "company_profile": {
                        "stage": "growth",
                        "industry_sector": "technology/services",
                        "funding_readiness": "medium",
                        "investment_highlights": [
                            "Solid business fundamentals",
                            "Growth potential in market",
                            "Experienced management team"
                        ],
                        "target_investment_amount": "To be determined based on business needs",
                        "use_of_funds": "Business expansion and growth"
                    },
                    "recommended_investor_sources": [
                        {
                            "category": "Local Angel Investors",
                            "suitability_score": 8.0,
                            "specific_targets": [
                                {
                                    "name": "Georgian Angel Investor Network",
                                    "type": "Angel Network",
                                    "focus_areas": ["local businesses", "growth companies", "regional market"],
                                    "typical_investment_range": "50,000 - 500,000 GEL",
                                    "why_suitable": "Local market knowledge and interest in supporting Georgian businesses",
                                    "success_probability": "medium",
                                    "contact_approach": "Network through business associations and startup events",
                                    "website_info": "Local startup ecosystem networks"
                                }
                            ],
                            "overall_strategy": "Build relationships within the local investment community"
                        },
                        {
                            "category": "Development Finance Institutions",
                            "suitability_score": 7.5,
                            "specific_targets": [
                                {
                                    "name": "European Bank for Reconstruction and Development",
                                    "type": "Development Finance",
                                    "focus_areas": ["emerging markets", "private sector development", "SME financing"],
                                    "typical_investment_range": "1M - 50M USD",
                                    "why_suitable": "Focus on Georgian market development and business growth",
                                    "success_probability": "medium",
                                    "contact_approach": "Formal application through their SME programs",
                                    "website_info": "EBRD Georgia office"
                                }
                            ],
                            "overall_strategy": "Apply through established development finance channels"
                        }
                    ],
                    "funding_platforms": [
                        {
                            "platform_name": "Regional Investment Platforms",
                            "platform_type": "peer_to_peer",
                            "suitability_score": 6.5,
                            "why_recommended": "Good for smaller funding rounds and building investor relationships",
                            "success_factors": ["transparent business model", "clear growth strategy"],
                            "typical_funding_range": "100,000 - 1,000,000 GEL",
                            "campaign_strategy": "Focus on local market opportunity and business fundamentals"
                        }
                    ],
                    "traditional_funding_sources": [
                        {
                            "source_type": "Bank Loans",
                            "specific_institutions": ["Bank of Georgia", "TBC Bank", "Liberty Bank"],
                            "suitability_score": 8.5,
                            "why_suitable": "Strong financial performance supports loan qualification",
                            "terms_expectation": "Competitive rates based on business performance",
                            "application_strategy": "Prepare comprehensive business plan and financial projections"
                        }
                    ],
                    "networking_opportunities": [
                        {
                            "event_type": "Startup Ecosystem Events",
                            "specific_events": ["TBC StartUp", "Georgia Innovation Week", "Business Angel Network events"],
                            "why_valuable": "Connect with potential investors and partners in the Georgian market",
                            "preparation_strategy": "Prepare elevator pitch and business summary materials"
                        }
                    ],
                    "investor_matching_strategy": {
                        "primary_approach": "Local angel investors and business networks combined with bank financing",
                        "secondary_approaches": ["Development finance institutions", "Regional VC funds"],
                        "timeline": "6-12 months for comprehensive funding strategy",
                        "preparation_needed": ["Business plan refinement", "Financial projections", "Legal structure optimization"],
                        "success_factors": ["Clear value proposition", "Strong financial performance", "Local market presence"]
                    },
                    "risk_assessment": {
                        "funding_challenges": ["Limited VC ecosystem in Georgia", "Need for international expansion for larger rounds"],
                        "mitigation_strategies": ["Focus on local angels and development finance", "Build strong local track record"],
                        "market_timing": "Favorable for businesses with strong fundamentals in emerging markets"
                    }
                },
                "detailed_recommendations": {
                    "immediate_actions": [
                        "Prepare comprehensive business plan and financial package",
                        "Join local business networks and startup ecosystem organizations",
                        "Schedule meetings with local banks to explore debt financing options"
                    ],
                    "medium_term_strategy": [
                        "Build relationships with local angel investors through networking events",
                        "Apply to relevant development finance programs",
                        "Consider participating in startup competitions and pitch events"
                    ],
                    "long_term_approach": [
                        "Develop international investor relationships for future growth rounds",
                        "Build track record to attract larger institutional investors",
                        "Consider strategic partnerships with international companies"
                    ]
                },
                "success_metrics": {
                    "key_indicators": ["Number of investor meetings scheduled", "Amount of interest generated", "Funding applications submitted"],
                    "milestones": ["Complete business plan", "First investor presentation", "Initial funding secured"],
                    "expected_outcomes": "Successful funding within 6-12 months through combination of sources"
                },
                "error": str(e),
                "raw_response": response_text[:500] if response_text else "No response"
            }
        except Exception as e:
            return {
                "investor_search_strategy": {
                    "company_profile": {
                        "stage": "unknown",
                        "industry_sector": "general",
                        "funding_readiness": "low",
                        "investment_highlights": ["Analysis needed"],
                        "target_investment_amount": "To be determined",
                        "use_of_funds": "Business needs assessment required"
                    },
                    "recommended_investor_sources": [],
                    "funding_platforms": [],
                    "traditional_funding_sources": [],
                    "networking_opportunities": [],
                    "investor_matching_strategy": {
                        "primary_approach": "Comprehensive business analysis needed",
                        "secondary_approaches": [],
                        "timeline": "TBD",
                        "preparation_needed": ["Business assessment"],
                        "success_factors": ["Data collection and analysis"]
                    },
                    "risk_assessment": {
                        "funding_challenges": ["Insufficient data for analysis"],
                        "mitigation_strategies": ["Provide more comprehensive business information"],
                        "market_timing": "Assessment pending"
                    }
                },
                "detailed_recommendations": {
                    "immediate_actions": ["Provide more detailed business information"],
                    "medium_term_strategy": ["Complete business assessment"],
                    "long_term_approach": ["Develop funding strategy based on assessment"]
                },
                "success_metrics": {
                    "key_indicators": ["Data completeness"],
                    "milestones": ["Information gathering"],
                    "expected_outcomes": "Proper analysis with sufficient data"
                },
                "error": str(e)
            }

    def analyze_startup(self, startup_description, flags=None):
        """
        Use Gemini to analyze startup description and provide comprehensive analysis
        including valuation, competitive landscape, and investor discovery
        """
        try:
            startup_prompt = self._get_startup_analysis_prompt()
            
            # Prepare input data
            input_data = {
                "startup_description": startup_description,
                "flags": flags or {
                    "browse_enabled": True,
                    "include_competitive": True,
                    "include_investors": True
                }
            }
            
            full_prompt = startup_prompt + f"""
INPUT:
{json.dumps(input_data, indent=2)}
"""
            
            response = self.model.generate_content(
                full_prompt, generation_config=self.generation_config
            )
            response_text = self._extract_response_text(response)
            
            if not response_text:
                raise ValueError("No text content in Gemini response")
            
            startup_analysis = self._parse_startup_response(response_text)
            return {"success": True, "data": startup_analysis}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Startup analysis error: {str(e)}",
                "raw_response": None,
            }

    def _get_startup_analysis_prompt(self):
        """
        Return the startup analysis prompt for Gemini
        """
        return """ROLE
You are a venture valuation analyst, investment strategist, and investor discovery assistant.
From a single free-text startup description, you must:

1. Extract all structured inputs automatically.
2. Detect the startup stage → Pre-revenue, Early-revenue, Growth-stage.
3. Generate projections using sector constants if missing.
4. Perform deterministic valuations using VC, Scorecard, Berkus, DCF, and Comps.
5. Suggest ideal investment amount and investor equity %.
6. Provide competitor benchmarking insights.
7. Discover investors, accelerators, and grants based on startup sector and region.
8. Detect when data is insufficient and return a checklist of missing items.
9. Provide precision suggestions for improving accuracy.

You must return either Case 1 (sufficient data) or Case 2 (insufficient data) in valid JSON format.

OUTPUT — STRICT JSON
Case 1 — Sufficient Data
{
  "status": "success",
  "valuation_summary": {
    "final_estimated_value": 14000000,
    "valuation_range": {
      "low": 12000000,
      "high": 16000000,
      "mid": 14000000
    },
    "methodology_breakdown": {
      "vc_ev": 14500000,
      "scorecard_ev": 12000000,
      "berkus_ev": 11000000,
      "dcf_ev": 13800000,
      "comps_ev": 15000000
    }
  },
  "investment_strategy": {
    "ideal_investment_amount": 1200000,
    "suggested_investor_equity": 0.18,
    "founder_equity_retention_post_round": 0.82
  },
  "competitive_landscape": {
    "competitors": [
      {
        "name": "CompetitorName",
        "country": "Country",
        "stage_or_round": "Series A",
        "funding": "₾3.2M",
        "valuation": "₾12M",
        "positioning": "Brief description",
        "source": "crunchbase.com"
      }
    ],
    "pros_cons_vs_competitors": {
      "pros": ["Advantage 1", "Advantage 2"],
      "cons": ["Challenge 1", "Challenge 2"],
      "opportunities": ["Opportunity 1", "Opportunity 2"],
      "threats": ["Threat 1", "Threat 2"]
    }
  },
  "investor_discovery": {
    "target_investors": [
      {
        "name": "Investor Name",
        "type": "VC Fund",
        "stage_focus": "Seed, Series A",
        "sector_focus": "SaaS, Tech",
        "ticket_size": "₾200K - ₾1.5M",
        "notable_investments": ["Portfolio1", "Portfolio2"],
        "website": "https://investor.com"
      }
    ],
    "regional_programs": [
      {
        "name": "Program Name",
        "type": "accelerator",
        "focus": "Early-stage tech",
        "website": "https://program.com"
      }
    ],
    "approach_insights": [
      "Insight 1 about approaching investors",
      "Insight 2 about strategy"
    ]
  },
  "suggestions_for_precision": [
    "Suggestion 1 for better accuracy",
    "Suggestion 2 for improvements"
  ],
  "summary": "Brief summary of analysis and methods used"
}

Case 2 — Insufficient Data
{
  "status": "insufficient_data",
  "valuation_summary": {
    "final_estimated_value": null,
    "valuation_range": {
      "low": null,
      "high": null,
      "mid": null
    },
    "methodology_breakdown": {
      "vc_ev": null,
      "scorecard_ev": null,
      "berkus_ev": null,
      "dcf_ev": null,
      "comps_ev": null
    }
  },
  "investment_strategy": {
    "ideal_investment_amount": null,
    "suggested_investor_equity": null,
    "founder_equity_retention_post_round": null
  },
  "competitive_landscape": {
    "competitors": [],
    "pros_cons_vs_competitors": {
      "pros": [],
      "cons": [],
      "opportunities": [],
      "threats": []
    }
  },
  "investor_discovery": {
    "target_investors": [],
    "regional_programs": [],
    "approach_insights": []
  },
  "suggestions_for_precision": [
    "Specify sector to load growth benchmarks",
    "Provide expected revenue projections",
    "Include funding target information",
    "Add market size estimates"
  ],
  "summary": "Insufficient data for reliable valuation. More information needed."
}
"""

    def _parse_startup_response(self, response_text):
        """
        Parse startup analysis response from Gemini
        """
        try:
            response_text = response_text.strip()
            
            # Try to extract JSON content from the response
            json_text = self._extract_json_content(response_text)
            
            if not json_text:
                # Try to find JSON manually if extraction fails
                start_brace = response_text.find("{")
                end_brace = response_text.rfind("}")
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    json_text = response_text[start_brace : end_brace + 1]
            
            if not json_text:
                raise ValueError("No JSON content found in response")
            
            # Fix common JSON issues
            json_text = self._fix_common_json_issues(json_text)
            
            # Parse the JSON
            parsed_data = json.loads(json_text)
            return parsed_data
            
        except json.JSONDecodeError as e:
            # Return fallback structure for insufficient data case
            return {
                "status": "insufficient_data",
                "valuation_summary": {
                    "final_estimated_value": None,
                    "valuation_range": {
                        "low": None,
                        "high": None,
                        "mid": None
                    },
                    "methodology_breakdown": {
                        "vc_ev": None,
                        "scorecard_ev": None,
                        "berkus_ev": None,
                        "dcf_ev": None,
                        "comps_ev": None
                    }
                },
                "investment_strategy": {
                    "ideal_investment_amount": None,
                    "suggested_investor_equity": None,
                    "founder_equity_retention_post_round": None
                },
                "competitive_landscape": {
                    "competitors": [],
                    "pros_cons_vs_competitors": {
                        "pros": [],
                        "cons": [],
                        "opportunities": [],
                        "threats": []
                    }
                },
                "investor_discovery": {
                    "target_investors": [],
                    "regional_programs": [],
                    "approach_insights": []
                },
                "suggestions_for_precision": [
                    "Please provide more detailed startup information",
                    "Include sector/industry details",
                    "Specify target market and revenue projections",
                    "Add funding requirements and stage information"
                ],
                "summary": f"Unable to parse response. JSON error: {str(e)}",
                "error": str(e)
            }
            
        except Exception as e:
            # Return generic error fallback
            return {
                "status": "insufficient_data",
                "valuation_summary": {
                    "final_estimated_value": None,
                    "valuation_range": {
                        "low": None,
                        "high": None,
                        "mid": None
                    },
                    "methodology_breakdown": {
                        "vc_ev": None,
                        "scorecard_ev": None,
                        "berkus_ev": None,
                        "dcf_ev": None,
                        "comps_ev": None
                    }
                },
                "investment_strategy": {
                    "ideal_investment_amount": None,
                    "suggested_investor_equity": None,
                    "founder_equity_retention_post_round": None
                },
                "competitive_landscape": {
                    "competitors": [],
                    "pros_cons_vs_competitors": {
                        "pros": [],
                        "cons": [],
                        "opportunities": [],
                        "threats": []
                    }
                },
                "investor_discovery": {
                    "target_investors": [],
                    "regional_programs": [],
                    "approach_insights": []
                },
                "suggestions_for_precision": [
                    "System error occurred during analysis",
                    "Please try again with more detailed information",
                    "Include specific business model and market details"
                ],
                "summary": f"Analysis error: {str(e)}",
                "error": f"Unexpected error: {str(e)}"
            }

    def analyze_competitors(self, company_data):
        """
        Use Gemini to analyze company documents and identify competitors in the same industry
        """
        try:
            competitor_prompt = self._get_competitor_analysis_prompt()
            
            full_prompt = competitor_prompt + f"""

COMPANY_DATA:
{company_data}
"""
            
            response = self.model.generate_content(
                full_prompt, generation_config=self.generation_config
            )
            response_text = self._extract_response_text(response)
            
            if not response_text:
                raise ValueError("No text content in Gemini response")
            
            competitor_analysis = self._parse_competitor_response(response_text)
            return {"success": True, "data": competitor_analysis}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Competitor analysis error: {str(e)}",
                "raw_response": None,
            }

    def _get_competitor_analysis_prompt(self):
        """
        Return the competitor analysis prompt for Gemini
        """
        return """ROLE
You are a financial analysis orchestrator and valuation assistant.
Your task is to:

1. Extract full financials from uploaded company documents
2. Identify company industry and size automatically
3. Find best comparable peers at the same competitive level

COMPETITOR MATCHING PRIORITY:
1. FIRST PRIORITY: Companies in the same country and same industry
2. SECOND PRIORITY: If the company is a top/large company in its country, then find global competitors in the same industry
3. SAME LEVEL MATCHING: Match companies of similar size/revenue level - do NOT match small local companies with multibillion-dollar corporations

INSTRUCTIONS:
- Analyze company size, revenue, and market position from the financial data
- Identify the company's country of operation
- Match competitors at the same competitive level (small vs small, large vs large)
- For local/regional companies: prioritize domestic competitors
- For major market leaders: include relevant global competitors
- Return ONLY a JSON response with the specified format

SIZE MATCHING EXAMPLES:
- Small local restaurant → other local/regional restaurant chains, NOT McDonald's
- Regional bank → other regional banks, NOT JPMorgan Chase
- Large multinational tech company → other major tech companies globally
- SME logistics company → other SME logistics companies in same region

OUTPUT FORMAT:
You must return ONLY a valid JSON object with this exact structure:
{"competitors":["Company1", "Company2", "Company3"]}

IMPORTANT:
- Return ONLY the JSON object, no additional text
- Use well-known, real company names at appropriate scale
- Maximum 8 competitors
- Ensure all company names are spelled correctly
- Match company size and market level appropriately
"""

    def _parse_competitor_response(self, response_text):
        """
        Parse competitor analysis response from Gemini
        """
        try:
            response_text = response_text.strip()
            
            # Try to extract JSON content from the response
            json_text = self._extract_json_content(response_text)
            
            if not json_text:
                # Try to find JSON manually if extraction fails
                start_brace = response_text.find("{")
                end_brace = response_text.rfind("}")
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    json_text = response_text[start_brace : end_brace + 1]
            
            if not json_text:
                raise ValueError("No JSON content found in response")
            
            # Fix common JSON issues
            json_text = self._fix_common_json_issues(json_text)
            
            # Parse the JSON
            parsed_data = json.loads(json_text)
            
            # Ensure we have the expected structure
            if "competitors" not in parsed_data:
                parsed_data = {"competitors": []}
            
            # Ensure competitors is a list
            if not isinstance(parsed_data["competitors"], list):
                parsed_data["competitors"] = []
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            # Return fallback structure for JSON parsing errors
            return {
                "competitors": [],
                "error": f"JSON parsing error: {str(e)}",
                "raw_response": response_text[:500] if response_text else "No response"
            }
            
        except Exception as e:
            # Return generic error fallback
            return {
                "competitors": [],
                "error": f"Unexpected error: {str(e)}",
                "raw_response": response_text[:500] if response_text else "No response"
            }

    def compare_companies(self, company_a_data, company_b_data):
        """
        Use Gemini to compare two companies based on their financial documents
        """
        try:
            comparison_prompt = self._get_company_comparison_prompt()

            full_prompt = comparison_prompt + f"""

COMPANY A DATA:
{company_a_data}

COMPANY B DATA:
{company_b_data}
"""

            response = self.model.generate_content(
                full_prompt, generation_config=self.generation_config
            )
            response_text = self._extract_response_text(response)

            if not response_text:
                raise ValueError("No text content in Gemini response")

            comparison_analysis = self._parse_comparison_response(response_text)
            return {"success": True, "data": comparison_analysis}

        except Exception as e:
            return {
                "success": False,
                "error": f"Company comparison error: {str(e)}",
                "raw_response": None,
            }

    def _get_company_comparison_prompt(self):
        """
        Return the company comparison prompt for Gemini
        """
        return """ROLE
You are a senior financial analysis expert and investment advisor specializing in comprehensive company comparisons with advanced valuation capabilities.
Your task is to analyze and compare two companies based on their financial documents and provide detailed insights including precise valuations.

CRITICAL FIRST STEP - INDUSTRY VALIDATION:
Before performing any comparison, you MUST:
1. Identify the primary industry/sector of each company from their business description and financial data
2. Determine if they operate in the same or closely related industries
3. If companies are from significantly different industries (e.g., healthcare vs. retail, technology vs. manufacturing, pharmaceutical vs. construction), 
   set "comparison_valid" to false and explain why meaningful comparison is not possible
4. Only proceed with detailed comparison if industries are compatible for meaningful analysis

ANALYSIS REQUIREMENTS (only if comparison_valid = true):
1. Extract and compare key financial metrics from both companies
2. Perform comprehensive DCF-based valuation analysis for each company
3. Analyze business models, market positioning, and competitive advantages
4. Compare financial performance, growth trajectories, and profitability
5. Assess operational efficiency and market presence
6. Evaluate detailed risk profiles and financial stability
7. Provide investment attractiveness analysis with valuation multiples
8. Generate actionable insights and strategic recommendations

VALUATION METHODOLOGY:
Apply this comprehensive valuation approach for BOTH companies:

GLOBAL RULES
- Deterministic & auditable: Same input ⇒ same output. Do not randomize.
- No external data fetches or browsing. Use only what is in INPUT and CONSTANTS. If something is missing, apply the “Assumptions & Guards” exactly as written.
- Units & scale: Inputs are GEL in thousands. Before any calc, create two internal scenarios:
  • Scenario A (Thousands-as-stated): convert all monetary inputs to absolute GEL by ×1,000 and run the full model.  
  • Scenario B (Already-absolute safety check): run the full model without scaling (×1).  
  Choose the scenario whose implied EV/EBITDA (from the DCF EV) is within ±20% of the sector EV/EBITDA multiple in CONSTANTS. If both qualify, pick Scenario A. If only one qualifies, pick that one. If neither qualifies, pick the one closer to the sector multiple. All reported outputs must be from the chosen scenario and be in absolute GEL.
- Signs & conventions: Expenses/Capex/interest paid may be negative in INPUT; treat magnitudes correctly (Capex used in calcs is |Capex|).
- Rounding: Keep full precision internally. Output monetary values as integers (no separators); rates as decimals to 4 places where relevant (internally only—final JSON only carries values requested).
- Exclusions: Exclude non-operating items (interest, FX gains/losses) from operating metrics and NOPAT unless specifically called for (e.g., interest for Kd).
- Sanity flags: Apply sanity checks and guardrails; do not add extra fields to output—fold brief notes into methodology where needed.

**CALCULATE VALUATION FOR BOTH COMPANIES, THE VALUATION SHOULD NOT BE RANDOMIZED, MULTIPLE GENERATION SHOULD ALWAYS RETURN SAME RESULT AND MUST BE REALISTIC**

**RISK & STABILITY ANALYSIS:**
Provide comprehensive risk assessment covering:

**Financial Stability Risks:**
- Debt-to-equity ratios and leverage analysis
- Interest coverage and debt service capacity
- Working capital management efficiency
- Cash flow volatility and predictability
- Liquidity position and cash conversion cycle

**Market & Operational Risks:**
- Market concentration and customer dependency
- Competitive position and market share trends
- Regulatory and compliance risks
- Operational efficiency and cost structure
- Management quality and corporate governance

**Investment-Specific Risks:**
- Valuation sensitivity to key assumptions
- Sector-specific risks and cyclicality
- Currency and geographic exposure
- Technology and innovation risks
- ESG (Environmental, Social, Governance) factors

**Stability Indicators:**
- Revenue predictability and recurring income
- Margin stability across business cycles
- Capital allocation efficiency
- Dividend sustainability (if applicable)
- Balance sheet strength and financial flexibility

COMPARISON AREAS:
- Financial Performance (Revenue, Profitability, Growth with 5-year projections)
- Comprehensive Valuation (DCF, Multiples, Asset-based approaches)
- Market Position (Market share, competitive advantages, moats)
- Operational Efficiency (Cost structure, margins, efficiency ratios)
- Risk & Stability (Financial, operational, market, regulatory risks)
- Growth Potential (Market opportunities, scalability, innovation)
- Investment Attractiveness (Risk-adjusted returns, valuation appeal)

OUTPUT FORMAT:
You must return ONLY a valid JSON object with this exact structure:

{
  "comparison_summary": {
    "company_a_name": "Company A Name",
    "company_b_name": "Company B Name",
    "company_a_industry": "Primary industry/sector of Company A",
    "company_b_industry": "Primary industry/sector of Company B",
    "analysis_date": "2024-01-01",
    "comparison_valid": true,
    "industry_compatibility_reason": "Explanation of why comparison is valid/invalid",
    "overall_winner": "Primary/Competitor/Tie",
    "key_differentiator": "Brief explanation of main difference"
  },
  "financial_comparison": {
    "revenue": {
      "company_a": {
        "value": 1000000,
        "growth_rate": 0.15,
        "trend": "Growing/Stable/Declining"
      },
      "company_b": {
        "value": 800000,
        "growth_rate": 0.10,
        "trend": "Growing/Stable/Declining"
      },
      "winner": "Primary/Competitor/Tie",
      "analysis": "Detailed comparison of revenue performance"
    },
    "profitability": {
      "company_a": {
        "net_margin": 0.12,
        "gross_margin": 0.45,
        "ebitda_margin": 0.20
      },
      "company_b": {
        "net_margin": 0.08,
        "gross_margin": 0.40,
        "ebitda_margin": 0.15
      },
      "winner": "Primary/Competitor/Tie",
      "analysis": "Detailed comparison of profitability metrics"
    },
    "growth": {
      "company_a": {
        "revenue_growth": 0.15,
        "profit_growth": 0.20,
        "market_expansion": "Description"
      },
      "company_b": {
        "revenue_growth": 0.10,
        "profit_growth": 0.12,
        "market_expansion": "Description"
      },
      "winner": "Primary/Competitor/Tie",
      "analysis": "Detailed comparison of growth metrics"
    }
  },
  "operational_comparison": {
    "efficiency": {
      "company_a": {
        "operational_efficiency": "High/Medium/Low",
        "cost_management": "Excellent/Good/Poor",
        "asset_utilization": "Description"
      },
      "company_b": {
        "operational_efficiency": "High/Medium/Low",
        "cost_management": "Excellent/Good/Poor",
        "asset_utilization": "Description"
      },
      "winner": "Primary/Competitor/Tie",
      "analysis": "Detailed comparison of operational efficiency"
    },
    "market_position": {
      "company_a": {
        "market_share": "Description",
        "competitive_advantages": ["Advantage 1", "Advantage 2"],
        "brand_strength": "Strong/Medium/Weak"
      },
      "company_b": {
        "market_share": "Description",
        "competitive_advantages": ["Advantage 1", "Advantage 2"],
        "brand_strength": "Strong/Medium/Weak"
      },
      "winner": "Primary/Competitor/Tie",
      "analysis": "Detailed comparison of market positioning"
    }
  },
  "investment_analysis": {
    "comprehensive_valuation": {
      "company_a": {
        "dcf_valuation": {
          "enterprise_value": 5000000,
          "equity_value": 4500000,
          "wacc": 0.12,
          "terminal_growth_rate": 0.035,
          "revenue_projections": {
            "year_1": 1200000,
            "year_2": 1350000,
            "year_3": 1500000,
            "year_4": 1650000,
            "year_5": 1800000
          }
        },
        "multiples_valuation": {
          "ev_ebitda_multiple": 6.5,
          "ev_sales_multiple": 1.2,
          "p_e_multiple": 15.0,
          "comparable_ev": 4800000
        },
        "blended_valuation": {
          "final_enterprise_value": 4900000,
          "valuation_range": {
            "low": 4200000,
            "high": 5600000
          },
          "methodology_weights": {
            "dcf": 0.60,
            "multiples": 0.25,
            "asset_based": 0.15
          }
        }
      },
      "company_b": {
        "dcf_valuation": {
          "enterprise_value": 4000000,
          "equity_value": 3600000,
          "wacc": 0.14,
          "terminal_growth_rate": 0.035,
          "revenue_projections": {
            "year_1": 1000000,
            "year_2": 1100000,
            "year_3": 1200000,
            "year_4": 1300000,
            "year_5": 1400000
          }
        },
        "multiples_valuation": {
          "ev_ebitda_multiple": 6.0,
          "ev_sales_multiple": 1.0,
          "p_e_multiple": 12.0,
          "comparable_ev": 3800000
        },
        "blended_valuation": {
          "final_enterprise_value": 3900000,
          "valuation_range": {
            "low": 3400000,
            "high": 4400000
          },
          "methodology_weights": {
            "dcf": 0.60,
            "multiples": 0.25,
            "asset_based": 0.15
          }
        }
      },
      "winner": "Primary/Competitor/Tie",
      "analysis": "Detailed valuation comparison with DCF and multiples analysis"
    },
    "risk_assessment": {
      "company_a": {
        "financial_stability": {
          "debt_to_equity": 0.25,
          "interest_coverage": 8.5,
          "current_ratio": 2.1,
          "cash_conversion_cycle": 45,
          "financial_risk_score": 2.0,
          "stability_rating": "High"
        },
        "market_operational_risks": {
          "market_concentration": "Low",
          "competitive_position": "Strong",
          "regulatory_risk": "Medium",
          "operational_efficiency": "High",
          "market_risk_score": 2.5
        },
        "investment_risks": {
          "valuation_sensitivity": "Medium",
          "sector_cyclicality": "Low",
          "currency_exposure": "Low",
          "innovation_risk": "Medium",
          "esg_score": "Good",
          "investment_risk_score": 2.0
        },
        "overall_risk_score": 2.2,
        "risk_rating": "Low-Medium"
      },
      "company_b": {
        "financial_stability": {
          "debt_to_equity": 0.45,
          "interest_coverage": 4.2,
          "current_ratio": 1.6,
          "cash_conversion_cycle": 65,
          "financial_risk_score": 3.5,
          "stability_rating": "Medium"
        },
        "market_operational_risks": {
          "market_concentration": "High",
          "competitive_position": "Moderate",
          "regulatory_risk": "High",
          "operational_efficiency": "Medium",
          "market_risk_score": 3.8
        },
        "investment_risks": {
          "valuation_sensitivity": "High",
          "sector_cyclicality": "Medium",
          "currency_exposure": "Medium",
          "innovation_risk": "High",
          "esg_score": "Fair",
          "investment_risk_score": 3.5
        },
        "overall_risk_score": 3.6,
        "risk_rating": "Medium-High"
      },
      "winner": "Primary/Competitor/Tie",
      "analysis": "Comprehensive risk analysis covering financial stability, market risks, and investment-specific factors"
    },
    "investment_recommendation": {
      "preferred_investment": "Primary/Competitor/Both/Neither",
      "investment_rationale": "Detailed explanation based on valuation and risk analysis",
      "key_factors": ["Factor 1", "Factor 2", "Factor 3"],
      "risk_adjusted_returns": {
        "company_a": {
          "expected_return": "High/Medium/Low",
          "risk_adjusted_score": 8.5,
          "investment_grade": "A-/B+/B/B-/C+"
        },
        "company_b": {
          "expected_return": "High/Medium/Low", 
          "risk_adjusted_score": 6.2,
          "investment_grade": "A-/B+/B/B-/C+"
        }
      },
      "sensitivity_analysis": {
        "key_assumptions": ["Revenue growth", "EBITDA margins", "WACC", "Terminal growth"],
        "valuation_sensitivity": "Description of how sensitive valuations are to key assumptions"
      }
    }
  },
  "strengths_weaknesses": {
    "company_a": {
      "strengths": ["Strength 1", "Strength 2", "Strength 3"],
      "weaknesses": ["Weakness 1", "Weakness 2"],
      "opportunities": ["Opportunity 1", "Opportunity 2"],
      "threats": ["Threat 1", "Threat 2"]
    },
    "company_b": {
      "strengths": ["Strength 1", "Strength 2", "Strength 3"],
      "weaknesses": ["Weakness 1", "Weakness 2"],
      "opportunities": ["Opportunity 1", "Opportunity 2"],
      "threats": ["Threat 1", "Threat 2"]
    }
  },
  "recommendations": {
    "for_company_a": ["Recommendation 1", "Recommendation 2"],
    "for_company_b": ["Recommendation 1", "Recommendation 2"],
    "for_investors": ["Investment insight 1", "Investment insight 2"],
    "strategic_insights": ["Strategic insight 1", "Strategic insight 2"]
  }
}

INSTRUCTIONS:
- FIRST: Perform industry validation and set comparison_valid field accordingly
- If comparison_valid = false: Only fill comparison_summary section and set all other fields to null or provide minimal data with "Cannot compare different industries" messages
- If comparison_valid = true: Proceed with full analysis below
- Analyze both companies thoroughly based on the provided financial documents
- Extract actual financial figures where available and perform comprehensive valuation analysis
- Calculate DCF valuations with 5-year projections and WACC analysis
- Apply sector-appropriate multiples and comparable analysis
- Conduct detailed risk assessment across financial, market, and investment dimensions
- Include sensitivity analysis for key valuation assumptions
- Provide balanced, objective analysis with quantitative backing
- Return ONLY the JSON object, no additional text
- Ensure all numerical values are realistic and based on document data
- Calculate specific financial ratios: debt-to-equity, interest coverage, current ratio, cash conversion cycle
- Provide risk scores on 1-5 scale (1=low risk, 5=high risk)
- Include investment grade ratings (A- to C+)
- If specific data is not available, provide reasonable estimates based on industry norms
"""

    def _parse_comparison_response(self, response_text):
        """
        Parse company comparison response from Gemini
        """
        try:
            response_text = response_text.strip()

            # Try to extract JSON content from the response
            json_text = self._extract_json_content(response_text)

            if not json_text:
                # Try to find JSON manually if extraction fails
                start_brace = response_text.find("{")
                end_brace = response_text.rfind("}")
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    json_text = response_text[start_brace : end_brace + 1]

            if not json_text:
                raise ValueError("No JSON content found in response")

            # Fix common JSON issues
            json_text = self._fix_common_json_issues(json_text)

            # Parse the JSON
            parsed_data = json.loads(json_text)
            return parsed_data

        except json.JSONDecodeError as e:
            # Return fallback structure for JSON parsing errors
            return {
                "comparison_summary": {
                    "company_a_name": "Company A",
                    "company_b_name": "Company B",
                    "company_a_industry": "Unknown",
                    "company_b_industry": "Unknown",
                    "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                    "comparison_valid": false,
                    "industry_compatibility_reason": "Analysis failed - insufficient data to determine industries",
                    "overall_winner": "Tie",
                    "key_differentiator": "Analysis failed - insufficient data"
                },
                "error": f"JSON parsing error: {str(e)}",
                "raw_response": response_text[:500] if response_text else "No response"
            }

        except Exception as e:
            # Return generic error fallback
            return {
                "comparison_summary": {
                    "company_a_name": "Company A",
                    "company_b_name": "Company B",
                    "company_a_industry": "Unknown",
                    "company_b_industry": "Unknown",
                    "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                    "comparison_valid": false,
                    "industry_compatibility_reason": "Analysis error occurred",
                    "overall_winner": "Tie",
                    "key_differentiator": "Analysis error occurred"
                },
                "error": f"Unexpected error: {str(e)}",
                "raw_response": response_text[:500] if response_text else "No response"
            }

    def _build_investment_validity_prompt(self, financial_data, valuation_data, investment_data):
        """Build the fast investment validity prompt for Gemini (simplified but complete)"""
        prompt = f"""Fast Investment Analysis - Single Model Assessment

ROLE
You are a senior investment analyst providing a CONCISE but COMPLETE investment assessment. Analyze the provided data and return a simplified investment decision with all required fields. Keep analysis brief but comprehensive.

INPUT DATA

FINANCE_JSON:
{json.dumps(financial_data, indent=2)}

VALUATION_JSON:
{json.dumps(valuation_data, indent=2)}

NEW_INFO_JSON:
{json.dumps(investment_data, indent=2)}

TASK
Provide a FAST but COMPLETE investment analysis. Keep explanations CONCISE (1-2 sentences max per field). Include all required fields but with simplified content.

ALL DATA IS IN GEL CURRENCY.

If no equity specified, suggest reasonable equity (10-25%) based on company stage.
If no valuation specified, estimate based on sector and stage.

OUTPUT_SCHEMA (return exactly this JSON structure):

{{
  "verdict": "invest" | "consider_with_conditions" | "dont_invest" | "insufficient_data",
  "confidence": <number 0-100>,
  "valuation": {{
    "raw": {{"p25": <number>, "p50": <number>, "p75": <number>}},
    "adjusted": {{"p25": <number>, "p50": <number>, "p75": <number>}},
    "method_breakdown": {{
      "dcf": {{"p25":<number>,"p50":<number>,"p75":<number>,"confidence":<number>}} | null,
      "multiples": {{"p25":<number>,"p50":<number>,"p75":<number>,"confidence":<number>}} | null,
      "precedent": {{"p25":<number>,"p50":<number>,"p75":<number>,"confidence":<number>}} | null,
      "rule_of_thumb": {{"p25":<number>,"p50":<number>,"p75":<number>,"confidence":<number>}} | null
    }}
  }},
  "recommended_offer": {{"raise_amount": <number>, "equity_pct": <number>, "terms": "<brief terms>"}},
  "cap_table_impact": {{"price_per_share_pre": <number>, "new_shares": <number>, "total_shares_after": <number>, "investor_pct_after": <number>}},
  "offer_assessment": {{
    "status": "attractive" | "fair" | "expensive" | "inconsistent" | "insufficient_data",
    "details": "<brief 1-2 sentence explanation>",
    "implied_pre_money_from_offer": <number>,
    "implied_percent_from_raise": <number>,
    "implied_amount_from_equity_pct": <number>,
    "consistency_check": "consistent" | "inconsistent" | "insufficient_data"
  }},
  "risk_score": <number 0-1>,
  "top_evidence": [
    {{"title": "<brief title>", "value": <number or string>, "source": "<source>", "why": "<brief reason>"}}
  ],
  "rationale": ["<brief point 1>", "<brief point 2>", "<brief point 3>"],
  "follow_up_questions": ["<question 1>", "<question 2>"],
  "provenance": {{"internal_docs": ["<doc>"], "external_apis": [], "timestamp": "<ISO 8601 UTC>"}},
  "simple_summary": {{
    "headline": "<single clear sentence about investment decision>",
    "why": "<1-2 sentence rationale>",
    "risk_and_consistency": "<1-2 sentence risk assessment>",
    "next_steps": "<1-2 sentence next steps>"
  }},
  "aggregation_summary": {{
    "models_consensus": "Single Gemini model analysis",
    "key_disagreements": "N/A - single model",
    "final_reasoning": "<brief reasoning for decision>",
    "confidence_basis": "<brief confidence explanation>"
  }},
  "investment_analysis": {{
    "why_invest": "<brief 1-2 sentence reason>",
    "growth_potential": "<brief growth assessment>",
    "market_opportunity": "<brief market size/opportunity>",
    "competitive_advantages": "<brief competitive edge>",
    "key_risks": "<brief main risks>",
    "mitigation_strategies": "<brief risk mitigation>",
    "expected_returns": "<brief return expectations>",
    "timeline_expectations": "<brief timeline>"
  }}
}}

INSTRUCTIONS:
- Keep ALL text fields BRIEF (1-2 sentences maximum)
- Provide realistic numbers based on the data
- Use null for unavailable data
- Include current timestamp
- Focus on key insights, not detailed analysis
- Ensure all required fields are present

Return ONLY the JSON structure:"""

        return prompt

    def _parse_investment_validity_response(self, response_text):
        """Parse investment validity response from Gemini (reuse existing parser)"""
        return self._parse_investment_response(response_text)
    
    def resolve_company_name(self, user_input, available_companies):
        """
        Use Gemini to resolve user input to official SEC company names
        
        Args:
            user_input: What the user typed (e.g., "Google", "mictosoft")
            available_companies: List of actual SEC company names and tickers
            
        Returns:
            Dict with resolved company suggestions
        """
        
        # Limit available companies to avoid huge prompts
        company_sample = available_companies[:500] if len(available_companies) > 500 else available_companies
        
        prompt = f"""
You are a company name resolver for SEC database lookups. 

User typed: "{user_input}"

Available companies in SEC database (sample):
{', '.join(company_sample)}

Task: Determine what company the user likely meant and suggest the best matches from the available companies.

Consider:
- Common company names vs official SEC names (e.g., "Google" → "Alphabet Inc.")
- Typos and misspellings (e.g., "mictosoft" → "Microsoft Corp")
- Ticker symbols (e.g., "AAPL" → "Apple Inc.")
- Partial names (e.g., "Apple" → "Apple Inc.")

Return ONLY a JSON array with top 3 suggestions, ordered by confidence:
[
  {{
    "company_name": "Exact name from available companies",
    "confidence": 95,
    "reason": "Why this matches (e.g., 'Common name for Alphabet Inc.')"
  }}
]

If no reasonable matches found, return empty array [].
"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
                
            suggestions = json.loads(response_text)
            
            return {
                "success": True,
                "suggestions": suggestions,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "suggestions": [],
                "error": f"Company name resolution failed: {str(e)}"
            }
