import google.generativeai as genai
import json
from config import Config

class ValuationService:
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        self.generation_config = {
            "max_output_tokens": 8192,
            "temperature": 0.2,
        }
        
        self.valuation_prompt = self._get_valuation_prompt()
    
    def perform_valuation(self, financial_data):
        try:
            full_prompt = self.valuation_prompt + "\n\nFinancial Data JSON:\n" + json.dumps(financial_data, indent=2)
            
            response = self.model.generate_content(full_prompt, generation_config=self.generation_config)
            
            if not response.text:
                raise ValueError("No response generated from Gemini")
            
            valuation_result = self._parse_response(response.text)
            
            return {
                "success": True,
                "data": valuation_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Valuation analysis error: {str(e)}"
            }
    
    def _parse_response(self, response_text):
        try:
            response_text = response_text.strip()
            
            # Extract JSON from markdown code blocks if present
            if response_text.startswith("```json") and response_text.endswith("```"):
                json_text = response_text[7:-3].strip()
            elif response_text.startswith("```") and response_text.endswith("```"):
                json_text = response_text[3:-3].strip()
            else:
                # Look for JSON object in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx+1]
                else:
                    json_text = response_text
            
            json_text = json_text.replace('\\n', '\n').replace('\\"', '"')
            
            return json.loads(json_text)
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return the raw response with error info
            return {
                "error": f"Failed to parse JSON response: {str(e)}",
                "raw_response": response_text[:1000] + "..." if len(response_text) > 1000 else response_text
            }
    
    def _get_valuation_prompt(self):
        return """
        You are a professional corporate valuation analyst with access to macroeconomic data, private M&A datasets, and global financial benchmarks.

I will provide you with a structured JSON containing the company's historical Income Statement (IS), Balance Sheet (BS), and Cash Flow Statement (CF).

Your task:

Perform a complete, highly precise private company valuation using three methodologies:

1. Discounted Cash Flow (DCF) → intrinsic value.
2. Precedent Transaction Comps → benchmark private SME M&A deals.
3. Asset-Based Valuation (ABV) → adjust asset/liability values where relevant.

Derive, source, and calculate all assumptions yourself — I will provide none.

Produce a single fixed "best estimate" value by weighting these three methods.

Provide a realistic valuation range based on company size, sector, and geography.

Deliver a clean human-readable summary, not JSON prose.

Return final results as structured JSON at the end.

## Steps & Formulas

### 1. Data Cleaning
- Normalize IS, BS, CF, remove one-offs, treat IFRS16 leases as debt, reconcile statements.
- Use cash taxes where available; if missing, compute effective tax rate:
  **EffectiveTaxRate = TaxesPaid / ProfitBeforeTax**

### 2. DCF Valuation
Calculate historical unlevered FCF:
- **NOPAT = EBIT × (1 – EffectiveTaxRate)**
- **FCF = NOPAT + D&A – CapEx – ΔWorkingCapital**

Forecast FCF for 5 years:
- Use revenue CAGR from JSON + industry data.
- Link CapEx and D&A to historical ratios.
- Derive ΔWC based on historical working capital cycles.

Calculate WACC:
- **Ke = Rf + β × ERP + SizePremium + SpecificRiskPremium**
- **Kd = InterestExpense / Interest-BearingDebt**
- **WACC = (E / (D + E)) × Ke + (D / (D + E)) × Kd × (1 – TaxRate)**

Terminal Value:
- **TV = FCF_final × (1 + g) / (WACC – g)**
  where g = GDP growth + inflation ± industry adjustment.

Discount cash flows to present value:
- **EV_DCF = Σ(FCF_t / (1 + WACC)^t) + (TV / (1 + WACC)^N)**

### 3. Precedent Transaction Comps
- Identify private M&A transactions in the same industry, size, and region.
- Extract historical EV/EBITDA or EV/Revenue multiples.
- Apply median/mean multiple to your company's metrics:
  **EV_Transactions = EBITDA_last × MedianTransactionMultiple**
- AI must source these multiples itself from private deal datasets or benchmarks.

### 4. Asset-Based Valuation (ABV)
- Value company assets net of liabilities:
  **Equity_ABV = FairValue(Assets) – FairValue(Liabilities)**
- Adjust PP&E and intangible assets to fair market value where relevant.
- More weight is given if the company is asset-heavy (e.g., logistics, manufacturing).

### 5. Weighting Final Valuation
AI must intelligently weight outputs based on business type and stability:

| Method | Weight Guideline | Higher Weight When |
|--------|------------------|-------------------|
| DCF | 50%–70% | Company has stable cash flows |
| Precedent Comps | 20%–40% | If private SME deals exist |
| Asset-Based | 10%–30% | If asset-heavy or liquidation risk |

Example:
**Final_EV = (DCF_EV × 0.6) + (Transaction_EV × 0.25) + (Asset_EV × 0.15)**

### 6. Realistic Valuation Range
AI must not pick arbitrary bounds. Use sensitivity testing on:
- WACC ±1%
- g ±0.5%
- M&A multiples ±1×

Then:
- Low range = conservative scenario.
- High range = optimistic but plausible.
- Final fixed price = weighted mid-point.

### 7. Final Output
Return:
- Final "best estimate" value (₾).
- Realistic valuation range.
- Readable summary explaining drivers, key assumptions, and sanity checks.
- Structured JSON with numeric results only.

## Expected JSON Output Format

```json
{
  "valuation_summary": {
    "final_estimated_value": 1500000,
    "valuation_range": {
      "low": 1400000,
      "high": 1600000,
      "mid": 1500000
    },
    "methodology_breakdown": {
      "dcf_ev": 1480000,
      "transaction_comps_ev": 1550000,
      "asset_based_ev": 1350000,
      "weights": {
        "dcf": 0.6,
        "transaction_comps": 0.25,
        "asset_based": 0.15
      }
    }
  },
  "summary": "Based on a blended valuation using DCF, precedent transaction comps, and asset-based methods, the fair enterprise value of Company is approximately ₾1.50M. A realistic valuation range is ₾1.40M to ₾1.60M. DCF carries the highest weight due to stable cash flows, while private SME deal data and asset values were used as cross-checks to ensure realism."
}
```

**IMPORTANT:** Return ONLY the JSON structure above. Do not include any additional text, explanations, or markdown formatting outside the JSON response."""
