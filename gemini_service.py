import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import black, blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os

load_dotenv()

class GeminiFinancialExtractor:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Configure generation parameters to prevent truncation
        self.generation_config = {
            "max_output_tokens": 8192,  # Increase max tokens to prevent truncation
            "temperature": 0.1,  # Lower temperature for more consistent JSON output
        }
        
        # Define the financial prompt
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
        
        # Register fonts that support Georgian characters
        self._register_fonts()
        
        # PDF styles
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            textColor=blue,
            fontName='DejaVuSans'
        )
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            textColor=black,
            fontName='DejaVuSans'
        )
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            fontName='DejaVuSans'
        )
    
    def _register_fonts(self):
        """Register fonts that support Georgian characters"""
        try:
            # Try to register DejaVu Sans which supports Georgian
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/TTF/DejaVuSans.ttf',
                '/System/Library/Fonts/Helvetica.ttc',  # macOS fallback
                '/Windows/Fonts/arial.ttf'  # Windows fallback
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                    return
            
            # If no suitable font found, use default
            print("Warning: No Georgian-compatible font found, using default font")
            
        except Exception as e:
            print(f"Warning: Could not register custom font: {e}")

    def extract_financial_data(self, document_text):
        try:
            full_prompt = self.financial_prompt + document_text
            
            response = self.model.generate_content(full_prompt, generation_config=self.generation_config)
            
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
                
                # Check if JSON appears to be truncated (doesn't end with proper closing braces)
                if not json_text.rstrip().endswith('}'):
                    # Try to find the last complete object and truncate there
                    last_brace = json_text.rfind('}')
                    if last_brace > 0:
                        # Find the matching opening brace
                        brace_count = 0
                        for i in range(last_brace, -1, -1):
                            if json_text[i] == '}':
                                brace_count += 1
                            elif json_text[i] == '{':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_text = json_text[:i+1] + '}'
                                    break
                
                financial_data = json.loads(json_text)
                print(financial_data["summerized_data"])
                
                # Generate PDF if summarized data is available
                pdf_result = None
                if "summerized_data" in financial_data and financial_data["summerized_data"]:
                    pdf_filename = f"financial_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    pdf_path = f"public/pdfs/{pdf_filename}"
                    pdf_result = self.create_summary_pdf(financial_data["summerized_data"], pdf_path)
                    if pdf_result["success"]:
                        pdf_result["public_url"] = f"/pdfs/{pdf_filename}"
                
                return {
                    "success": True,
                    "data": financial_data,
                    "pdf_result": pdf_result
                }
            except json.JSONDecodeError as e:
                # If JSON parsing still fails, try to extract partial data
                try:
                    # Look for the financial_analysis section specifically
                    if '"financial_analysis"' in json_text:
                        start_idx = json_text.find('"financial_analysis"')
                        # Find the opening brace after financial_analysis
                        brace_start = json_text.find('{', start_idx)
                        if brace_start > 0:
                            # Try to find a complete financial_analysis object
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
                                return {
                                    "success": True,
                                    "data": {"financial_analysis": financial_data},
                                }
                except:
                    pass
                
                return {
                    "success": False,
                    "error": f"Failed to parse JSON response from Gemini: {str(e)}",
                }
                
        except Exception as e:
                            return {
                    "success": False,
                    "error": f"Gemini API error: {str(e)}",
                    "raw_response": None
                }
    
    def _sanitize_text(self, text):
        """Sanitize text for PDF generation, handling Georgian characters"""
        if not isinstance(text, str):
            text = str(text)
        
        # Replace problematic characters that might cause PDF issues
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        return text
    
    def _format_key(self, key):
        """Format dictionary keys for display"""
        return key.replace('_', ' ').replace('-', ' ').title()
    
    def _process_data_recursively(self, data, story, level=0, max_level=5):
        """Recursively process nested data structures"""
        if level > max_level:
            story.append(Paragraph("... (data too deeply nested)", self.normal_style))
            return
        
        if isinstance(data, dict):
            for key, value in data.items():
                formatted_key = self._format_key(key)
                sanitized_key = self._sanitize_text(formatted_key)
                
                if isinstance(value, dict):
                    story.append(Paragraph(f"<b>{sanitized_key}</b>", self.heading_style if level == 0 else self.normal_style))
                    self._process_data_recursively(value, story, level + 1, max_level)
                    story.append(Spacer(1, 8 if level == 0 else 4))
                elif isinstance(value, list):
                    story.append(Paragraph(f"<b>{sanitized_key}</b>", self.heading_style if level == 0 else self.normal_style))
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            story.append(Paragraph(f"Item {i+1}:", self.normal_style))
                            self._process_data_recursively(item, story, level + 1, max_level)
                        else:
                            sanitized_item = self._sanitize_text(item)
                            story.append(Paragraph(f"• {sanitized_item}", self.normal_style))
                    story.append(Spacer(1, 8 if level == 0 else 4))
                else:
                    sanitized_value = self._sanitize_text(value)
                    if level == 0:
                        story.append(Paragraph(f"<b>{sanitized_key}</b>: {sanitized_value}", self.normal_style))
                    else:
                        story.append(Paragraph(f"• {sanitized_key}: {sanitized_value}", self.normal_style))
                    story.append(Spacer(1, 4))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    story.append(Paragraph(f"Item {i+1}:", self.normal_style))
                    self._process_data_recursively(item, story, level + 1, max_level)
                else:
                    sanitized_item = self._sanitize_text(item)
                    story.append(Paragraph(f"• {sanitized_item}", self.normal_style))
        else:
            sanitized_data = self._sanitize_text(data)
            story.append(Paragraph(sanitized_data, self.normal_style))

    def create_summary_pdf(self, summarized_data, output_path="financial_summary.pdf"):
        try:
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            story = []
            
            # Title
            story.append(Paragraph("Financial Analysis Summary", self.title_style))
            story.append(Spacer(1, 12))
            
            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            story.append(Paragraph(f"Generated on: {timestamp}", self.normal_style))
            story.append(Spacer(1, 20))
            
            # Process summarized data recursively
            self._process_data_recursively(summarized_data, story)
            
            doc.build(story)
            return {"success": True, "file_path": output_path}
            
        except Exception as e:
            return {"success": False, "error": f"PDF generation failed: {str(e)}"}
        
