import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

class GeminiFinancialExtractor:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        self.financial_prompt = """
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

**ADDITIONAL EXTRACTION - Also extract any other financial data you find:**
- Company information (name, industry, business description)
- Additional financial metrics and ratios
- Growth metrics and year-over-year comparisons
- Risk factors and investment highlights
- Market data and competitive information
- Any other relevant financial information

Please provide the response in the following JSON structure:
{
  "company_info": {
    "name": "string",
    "industry": "string",
    "description": "string"
  },
  "income_statement": {
    "revenue_sales": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "შემოსავალი რეალიზაციიდან"},
    "cogs": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "რეალიზებული პროდუქციის თვითღირებულება"},
    "gross_profit": {"current": "number", "previous": "number", "currency": "string", "note": "calculated"},
    "operating_expenses": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "საოპერაციო ხარჯები / გაყიდვების & ადმინისტრაციული ხარჯები"},
    "depreciation_amortization": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "ამორტიზაცია და ცვეთა"},
    "other_operating_income_expense": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "სხვა საოპერაციო შემოსავლები/ხარჯები"},
    "operating_profit_ebit": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "საოპერაციო მოგება"},
    "interest_expense": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "საპროცენტო ხარჯები"},
    "interest_income": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "საპროცენტო შემოსავლები"},
    "foreign_exchange_gains_losses": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "კურსთაშორისი სხვაობები"},
    "profit_before_tax_ebt": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "მოგება გადასახადამდე"},
    "income_tax_expense": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "მოგების გადასახადი"},
    "net_income": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "წმინდა მოგება"}
  },
  "balance_sheet": {
    "cash_equivalents": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "ფულადი სახსრები"},
    "accounts_receivable": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "ვალდებულებები დებიტორებისგან"},
    "inventory": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "მარაგები"},
    "other_current_assets": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "სხვა მიმდინარე აქტივები"},
    "ppe": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "ქონება, მცენარეები და ტექნიკა"},
    "intangible_assets": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "არამატერიალური აქტივები"},
    "accounts_payable": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "ვალდებულებები მომწოდებლების მიმართ"},
    "short_term_debt": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "მოკლევადიანი სესხები"},
    "long_term_debt": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "გრძელვადიანი სესხები"},
    "deferred_tax_liabilities": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "გადავადებული გადასახადები"},
    "shareholders_equity": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "კაპიტალი"}
  },
  "cash_flow_statement": {
    "cash_flow_from_operations": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "საოპერაციო საქმიანობიდან მიღებული ფულადი ნაკადები"},
    "taxes_paid": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "გადახდილი მოგების გადასახადი"},
    "interest_paid": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "გადახდილი საპროცენტო ხარჯები"},
    "capital_expenditures": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "ინვესტიციები ქონებაში, მცენარეებში, ტექნიკაში"},
    "changes_in_working_capital": {"current": "number", "previous": "number", "currency": "string", "georgian_term": "სამუშაო კაპიტალის ცვლილებები"},
    "free_cash_flow": {"current": "number", "previous": "number", "currency": "string", "note": "calculated"}
  },
  "additional_financial_data": {
    "ratios": {
      "profit_margin": "number",
      "roe": "number",
      "roa": "number",
      "debt_to_equity": "number",
      "current_ratio": "number",
      "pe_ratio": "number"
    },
    "growth_metrics": {
      "revenue_growth": "number",
      "profit_growth": "number",
      "yoy_comparison": "string"
    },
    "risk_factors": ["string"],
    "investment_highlights": ["string"],
    "market_data": {
      "market_cap": {"value": "number", "currency": "string"},
      "shares_outstanding": "number"
    }
  },
  "extraction_notes": "string"

If any information is not available, use null for that field. Be precise with numbers and include currency information when available. Focus on extracting quantitative data and key qualitative insights that would be valuable for investment analysis.

Document content to analyze:
"""

    def extract_financial_data(self, document_text):
        try:
            full_prompt = self.financial_prompt + document_text
            
            response = self.model.generate_content(full_prompt)
            
            if not response.text:
                raise ValueError("No response generated from Gemini")
            
            try:
                # Extract JSON from markdown code blocks if present
                response_text = response.text.strip()
                
                # Check if response is wrapped in markdown code blocks
                if response_text.startswith("```json") and response_text.endswith("```"):
                    # Remove the markdown code block markers
                    json_text = response_text[7:-3].strip()  # Remove ```json and ```
                elif response_text.startswith("```") and response_text.endswith("```"):
                    # Handle generic code blocks
                    json_text = response_text[3:-3].strip()  # Remove ``` and ```
                else:
                    # Use the response as-is
                    json_text = response_text
                
                # Clean up escaped newlines and other escape sequences
                json_text = json_text.replace('\\n', '\n').replace('\\"', '"')
                
                financial_data = json.loads(json_text)
                return {
                    "success": True,
                    "data": financial_data,
                    "raw_response": response.text
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Failed to parse JSON response from Gemini: {str(e)}",
                    "raw_response": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini API error: {str(e)}",
                "raw_response": None
            }
    
    def get_investment_recommendation(self, financial_data):
        if not financial_data.get("success"):
            return {"error": "Cannot generate recommendation without valid financial data"}
        
        recommendation_prompt = f"""
Based on the following extracted financial data, provide an investment recommendation and analysis:

{json.dumps(financial_data.get('data', {}), indent=2)}

Please provide:
1. Overall investment recommendation (Buy/Hold/Sell)
2. Key strengths and weaknesses
3. Risk assessment (Low/Medium/High)
4. Price target or valuation range (if possible)
5. Key factors to monitor

Format as JSON:
{{
  "recommendation": "Buy/Hold/Sell",
  "confidence": "High/Medium/Low",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "risk_level": "Low/Medium/High",
  "price_target": "string",
  "key_monitors": ["string"],
  "summary": "string"
}}
"""
        
        try:
            response = self.model.generate_content(recommendation_prompt)
            
            if not response.text:
                raise ValueError("No recommendation response generated")
            
            try:
                # Extract JSON from markdown code blocks if present
                response_text = response.text.strip()
                
                # Check if response is wrapped in markdown code blocks
                if response_text.startswith("```json") and response_text.endswith("```"):
                    # Remove the markdown code block markers
                    json_text = response_text[7:-3].strip()  # Remove ```json and ```
                elif response_text.startswith("```") and response_text.endswith("```"):
                    # Handle generic code blocks
                    json_text = response_text[3:-3].strip()  # Remove ``` and ```
                else:
                    # Use the response as-is
                    json_text = response_text
                
                # Clean up escaped newlines and other escape sequences
                json_text = json_text.replace('\\n', '\n').replace('\\"', '"')
                
                recommendation = json.loads(json_text)
                return {
                    "success": True,
                    "recommendation": recommendation
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Failed to parse recommendation JSON: {str(e)}",
                    "raw_response": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Recommendation generation error: {str(e)}"
            }
