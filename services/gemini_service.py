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
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        self.generation_config = {
            "max_output_tokens": 8192,
            "temperature": 0.1,
        }
        
        self.pdf_generator = PDFGenerator()
        self.financial_prompt = self._get_financial_prompt()
    
    def extract_financial_data(self, document_text):
        try:
            full_prompt = self.financial_prompt + document_text
            response = self.model.generate_content(full_prompt, generation_config=self.generation_config)
            
            if not response.text:
                raise ValueError("No response generated from Gemini")
            
            financial_data = self._parse_response(response.text)
            pdf_result = self._generate_pdf_if_needed(financial_data)
            
            return {
                "success": True,
                "data": financial_data,
                "pdf_result": pdf_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini API error: {str(e)}",
                "raw_response": None
            }
    
    def _parse_response(self, response_text):
        try:
            response_text = response_text.strip()
            
            if response_text.startswith("```json") and response_text.endswith("```"):
                json_text = response_text[7:-3].strip()
            elif response_text.startswith("```") and response_text.endswith("```"):
                json_text = response_text[3:-3].strip()
            else:
                json_text = response_text
            
            json_text = json_text.replace('\\n', '\n').replace('\\"', '"')
            
            if not json_text.rstrip().endswith('}'):
                json_text = self._fix_truncated_json(json_text)
            
            return json.loads(json_text)
            
        except json.JSONDecodeError as e:
            partial_data = self._extract_partial_data(json_text)
            if partial_data:
                return partial_data
            
            raise ValueError(f"Failed to parse JSON response from Gemini: {str(e)}")
    
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

Besides it, save all available financial data to the summerized data field, including summerized info about company, everthing important.

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

**IMPORTANT:** Extract data for ALL available years found in the document, not just the example years shown above. Use the actual years from the financial statements (e.g., 2019, 2020, 2021, 2022, 2023, 2024, etc.). If any information is not available for a specific year, use null for that field. Include extraction_notes for any items that could not be found or extracted. Be precise with numbers and focus on extracting quantitative data that would be valuable for investment analysis.

Document content to analyze:
"""
