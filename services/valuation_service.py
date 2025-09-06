import google.generativeai as genai
import json
import hashlib
from datetime import datetime
from config import Config
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


class ValuationService:
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Original Gemini setup (keeping as fallback)
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

        self.generation_config = {
            "max_output_tokens": 8192,
            "temperature": 0.2,
        }

        # LangChain setup
        self.langchain_llm = GoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=Config.GEMINI_API_KEY,
            temperature=0.2,
            max_output_tokens=8192
        )
        
        # Memory for caching valuations (per-session)
        self.valuation_memory = {}
        
        # Create simple prompt template (avoiding complex formatting issues)
        self.valuation_prompt_text = self._get_valuation_prompt()
        
        # Create LangChain chain without template (due to complex prompt formatting)
        # We'll manually format the prompt in the method
        self.valuation_chain = None  # Will use direct LLM calls

    def perform_valuation(self, financial_data):
        try:
            # Generate memory key based on company name + timestamp (within same day)
            memory_key = self._generate_memory_key(financial_data)
            
            # Check if we have cached result
            if memory_key in self.valuation_memory:
                print(f"DEBUG: Using cached valuation for key: {memory_key}")
                return {"success": True, "data": self.valuation_memory[memory_key], "cached": True}
            
            print(f"DEBUG: Computing new valuation for key: {memory_key}")
            
            # Use LangChain LLM directly (avoiding template formatting issues)
            full_prompt = (
                self.valuation_prompt_text
                + "\n\nFinancial Data JSON:\n"
                + json.dumps(financial_data, indent=2)
            )
            response = self.langchain_llm.invoke(full_prompt)

            if not response:
                raise ValueError("No response generated from LangChain")

            valuation_result = self._parse_response(response)
            
            # Cache the result
            self.valuation_memory[memory_key] = valuation_result
            print(f"DEBUG: Cached valuation result for key: {memory_key}")

            return {"success": True, "data": valuation_result, "cached": False}

        except Exception as e:
            print(f"DEBUG: LangChain valuation failed: {e}, falling back to original Gemini")
            # Fallback to original method
            try:
                full_prompt = (
                    self.valuation_prompt_text
                    + "\n\nFinancial Data JSON:\n"
                    + json.dumps(financial_data, indent=2)
                )

                response = self.model.generate_content(
                    full_prompt, generation_config=self.generation_config
                )

                if not response.text:
                    raise ValueError("No response generated from Gemini")

                valuation_result = self._parse_response(response.text)

                return {"success": True, "data": valuation_result, "fallback": True}

            except Exception as fallback_e:
                return {"success": False, "error": f"Valuation analysis error: {str(fallback_e)}"}

    def _generate_memory_key(self, financial_data):
        """Generate memory key based on company data + date for caching"""
        try:
            # Try to extract company name from various possible locations
            company_name = "unknown"
            
            # Look for company name in balance sheet or income statement
            if isinstance(financial_data, dict):
                # Check for common company identifier fields
                if "company_name" in financial_data:
                    company_name = financial_data["company_name"]
                elif "entity_name" in financial_data:
                    company_name = financial_data["entity_name"]
                elif "sector" in financial_data:
                    # Use sector + revenue as proxy identifier
                    sector = financial_data.get("sector", "unknown")
                    revenue_2023 = None
                    if "income_statement" in financial_data and "revenue_sales" in financial_data["income_statement"]:
                        revenue_2023 = financial_data["income_statement"]["revenue_sales"].get("2023", 0)
                    company_name = f"{sector}_{revenue_2023}" if revenue_2023 else sector
            
            # Get today's date for daily cache expiry
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Create hash of financial data for uniqueness
            data_str = json.dumps(financial_data, sort_keys=True)
            data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]
            
            memory_key = f"{company_name}_{today}_{data_hash}"
            return memory_key
        except Exception as e:
            # Fallback to just data hash + date
            data_str = json.dumps(financial_data, sort_keys=True)
            data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]
            today = datetime.now().strftime("%Y-%m-%d")
            return f"unknown_{today}_{data_hash}"

    def _parse_response(self, response_text):
        try:
            response_text = response_text.strip()

            if response_text.startswith("```json") and response_text.endswith("```"):
                json_text = response_text[7:-3].strip()
            elif response_text.startswith("```") and response_text.endswith("```"):
                json_text = response_text[3:-3].strip()
            else:
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}")
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = response_text[start_idx : end_idx + 1]
                else:
                    json_text = response_text

            json_text = json_text.replace("\\n", "\n").replace('\\"', '"')

            return json.loads(json_text)

        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse JSON response: {str(e)}",
                "raw_response": (response_text),
            }

    def _get_valuation_prompt(self):
        return """
AI Valuation Prompt — Excel-Style, Fully Deterministic, Scale-Safe (with DCF, Comps, Precedents, Asset-Based) + Basic Calcs

ROLE
You are a senior valuation analyst replicating a full Excel-based SME valuation model. Perform every deterministic calculation in strict Excel order (no shortcuts, no hidden steps). Use AI judgment only for assumptions explicitly allowed below (sector multiples, WACC inputs, beta, terminal growth, market sentiment guardrails). Everything else is mechanical math.

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

INPUT (paste your data)
{
  "income_statement": {
    "cogs": { "2022": 448212, "2023": 499500 },
    "depreciation_amortization": { "2022": 16441, "2023": 18964 },
    "foreign_exchange_gains_losses": { "2022": -18927, "2023": 205 },
    "gross_profit": { "2022": 127885, "2023": 164848 },
    "income_tax_expense": { "2022": 0, "2023": 0 },
    "interest_expense": { "2022": 4711, "2023": 4178 },
    "interest_income": { "2022": 215, "2023": 270 },
    "net_income": { "2022": 38545, "2023": 51735 },
    "operating_expenses": { "2022": 107611, "2023": 125922 },
    "operating_profit_ebit": { "2022": 23664, "2023": 40960 },
    "other_operating_income_expense": { "2022": 3449, "2023": 2134 },
    "profit_before_tax_ebt": { "2022": 38545, "2023": 51735 },
    "revenue_sales": { "2022": 576097, "2023": 664348 }
  },
  "balance_sheet": {
    "accounts_payable": { "2022": 128553, "2023": 139523 },
    "accounts_receivable": { "2022": 44093, "2023": 64324 },
    "cash_equivalents": { "2022": 4556, "2023": 8158 },
    "deferred_tax_liabilities": { "2022": 0, "2023": 0 },
    "intangible_assets": { "2022": 2330, "2023": 2236 },
    "inventory": { "2022": 193195, "2023": 212263 },
    "long_term_debt": { "2022": 1858, "2023": 487 },
    "other_current_assets": { "2022": 0, "2023": 0 },
    "ppe": { "2022": 44591, "2023": 49321 },
    "shareholders_equity": { "2022": 227513, "2023": 274224 },
    "short_term_debt": { "2022": 9100, "2023": 1432 }
  },
  "cash_flow_statement": {
    "capital_expenditures": { "2022": -10990, "2023": -11544 },
    "cash_flow_from_operations": { "2022": 23603, "2023": 26599 },
    "changes_in_working_capital": { "2022": -13172, "2023": -30407 },
    "free_cash_flow": { "2022": 12613, "2023": 15055 },
    "interest_paid": { "2022": -4911, "2023": -4475 },
    "taxes_paid": { "2022": 0, "2023": 0 }
  },
  "sector": "Retail"
}

CONSTANTS & POLICIES (paste your constants)
{
  "constants": {
    "risk_free_rate": 0.0758,
    "equity_risk_premium": 0.05,
    "country_risk_premium": 0.04,
    "terminal_growth_rate": 0.035,
    "normalized_tax_rate": 0.15,
    "min_wacc": 0.10,
    "max_wacc": 0.18
  },
  "sector_multiples": {
    "Pharma": { "ev_ebitda": 9.0, "ev_sales": 1.8, "p_e": 18 },
    "Retail": { "ev_ebitda": 6.5, "ev_sales": 0.9, "p_e": 12 },
    "Logistics": { "ev_ebitda": 5.8, "ev_sales": 0.7, "p_e": 10.5 }
  },
  "precedent_multiples": {
    "Pharma": { "ev_ebitda": 8.5, "ev_sales": 1.7 },
    "Retail": { "ev_ebitda": 6.0, "ev_sales": 0.8 },
    "Logistics": { "ev_ebitda": 5.5, "ev_sales": 0.6 }
  },
  "capital_structure_policy": {
    "Retail": { "target_debt_weight": 0.20 }
  },
  "credit_spread_policy": {
    "base_spread": 0.03,
    "min_kd": 0.09,
    "max_kd": 0.20
  },
  "sanity_thresholds": {
    "multiple_deviation": 0.20,
    "cfo_bridge_tolerance": 0.10
  }
}

ASSUMPTIONS & GUARDS (apply exactly)
- If income tax expense equals 0 or <5% of EBT, use normalized_tax_rate for NOPAT and for the tax shield in WACC.
- Beta defaults by sector if not provided: Retail = 1.0 (extend similarly if sector implies other defaults in your policy; if not, use 1.0).
- Debt weight: if observed weights are noisy/negative (e.g., equity ≤ 0 or debt+equity ≤ 0), use sector policy target_debt_weight; else use observed book weights.
- Cost of Debt (Kd): observed Kd = interest_expense / average interest-bearing debt (Debt_t + Debt_t-1)/2. If average debt ≈ 0, or observed Kd < min_kd or > max_kd, set Kd = clamp(Rf + base_spread, min_kd, max_kd).
- Asset-based NAV: if total assets/liabilities not available, proxy NAV = shareholders_equity (book). If non-core items are explicitly provided, adjust NAV modestly and disclose the adjustment in methodology text (do not add fields).
- Scale safety: Run both scenarios (Thousands vs Absolute) as described under GLOBAL RULES and choose per rule.
- CFO bridge tolerance: if |CFO − (NI + D&A − ΔNWC)| > tolerance × |CFO|, treat as a warning; proceed.

STEP 1 — HISTORICAL CALCULATIONS (Latest two years, strict Excel order, using chosen scenario units)
Let 2022 = t−1, 2023 = t.

A) Consistency checks
1) GP_check_t: GP ?= Revenue − COGS. Flag if |difference| / Revenue > 1%.
2) EBIT_check_t: EBIT ?= GP − OpEx + Other Op. Flag if >1%.
3) NI_check_t: NI ?= EBT − Taxes. Flag if >1%.

B) Growth & deltas
4) ΔRevenue = Revenue_t − Revenue_{t−1}; Revenue_Growth = ΔRevenue / Revenue_{t−1}.
5) ΔEBITDA, ΔEBIT, ΔNI (absolute and %).
6) 2-yr CAGR (Revenue): CAGR = (Revenue_t / Revenue_{t−1})^(1) − 1.

C) Margins
7) EBITDA_t = EBIT_t + D&A_t; EBITDA_Margin = EBITDA_t / Revenue_t.
8) Gross_Margin = GP_t / Revenue_t; EBIT_Margin = EBIT_t / Revenue_t; Net_Margin = NI_t / Revenue_t.
9) OpEx_%Rev = OpEx_t / Revenue_t.

D) Working capital & efficiency
10) DSO = AR_t / Revenue_t × 365.
11) DIO = Inventory_t / COGS_t × 365.
12) DPO = AP_t / COGS_t × 365.
13) CCC = DSO + DIO − DPO.
14) NWC_t = AR_t + Inventory_t − AP_t.
15) ΔNWC = NWC_t − NWC_{t−1}.
16) NWC_%Rev for both years.

E) Capex, D&A, PP&E roll-forward sanity
17) Capex_%Rev = |Capex_t| / Revenue_t.
18) D&A_%Rev = D&A_t / Revenue_t.
19) PP&E_roll: Check PP&E_t ≈ PP&E_{t−1} + Capex_t − D&A_t. Note variance qualitatively (no extra fields).

F) Capital structure & coverage
20) Debt_{year} = Short_Term_Debt + Long_Term_Debt.
21) AvgDebt = (Debt_t + Debt_{t−1}) / 2.
22) Net_Debt_t = Debt_t − Cash_t.
23) Interest_Coverage = EBIT_t / InterestExpense_t (and CFO/Interest as secondary).
24) Leverage ratios: Net_Debt/EBITDA_t; Debt/Equity (book).

G) Tax, NOPAT, ROIC
25) Effective_Tax_t = Taxes_t / EBT_t if valid; else use normalized_tax_rate.
26) NOPAT_t = EBIT_t × (1 − tax_rate_used).
27) Operating_Invested_Capital (IC)_t = NWC_t + Net_PP&E_t + Intangibles_t − Deferred_Tax_Liab_t (use 0 if not provided).
28) Avg_IC = (IC_t + IC_{t−1}) / 2.
29) ROIC = NOPAT_t / Avg_IC (if Avg_IC ≈ 0, skip ratio and proceed).

H) Cash flow bridges
30) UFCF_hist_t = NOPAT_t + D&A_t − |Capex_t| − ΔNWC.
31) CFO bridge: CFO ?≈ NI + D&A − ΔNWC (apply tolerance policy). Note warning if exceeded.
32) FCF_yield_spot = UFCF_hist_t / Revenue_t.

STEP 2 — FORECASTS (Y+1…Y+5, absolute GEL, derived mechanically)
33) Revenue path: start from Revenue_t. Growth follows: begin at 2-yr CAGR and linearly fade to terminal_growth_rate by Y+5.
34) EBITDA margin: use 2-yr median; if extreme outlier, gently converge toward that median by Y+5.
35) D&A% and Capex% of Revenue: use simple 2-yr averages.
36) Working capital days: DSO/DIO/DPO = 2-yr averages; recompute NWC each forecast year from these days and derive ΔNWC annually.
37) Tax rate: use tax_rate_used from Step 1G (normalized if needed).
38) For each forecast year: compute EBITDA, EBIT (EBIT = EBITDA − D&A), NOPAT = EBIT × (1−tax), UFCF = NOPAT + D&A − Capex − ΔNWC.

STEP 3 — VALUATION MODELS
A) DCF (Unlevered FCF)
39) WACC:
   - Ke = Rf + β × ERP + CRP. If β missing, use sector default (Retail=1.0).  
   - Kd observed = InterestExpense_t / AvgDebt (from Step 1F). If invalid or out of bounds, set per credit_spread_policy: Kd = clamp(Rf + base_spread, min_kd, max_kd).  
   - Weights: If observed book weights noisy/invalid, use sector target_debt_weight; otherwise use observed book D/V and E/V.  
   - After-tax Kd = Kd × (1 − tax_rate_used).  
   - WACC = We×Ke + Wd×After-tax Kd; clamp to [min_wacc, max_wacc].
40) Discount factors (end-of-year): DF_y = 1 / (1 + WACC)^y for y=1..5.
41) PV(FCFs) = Σ [UFCF_y × DF_y], y=1..5.
42) Terminal value (TV) at Y+5: TV = UFCF_{Y+5} × (1 + g) / (WACC − g), g = terminal_growth_rate.
43) PV(TV) = TV × DF_5.
44) EV_DCF = PV(FCFs) + PV(TV).
45) Exit-multiple cross-check: compute implied EV/EBITDA at Y+5 using EV_Terminal_Only = TV (pre-discount) and EBITDA_{Y+5}; compare to sector multiple for sanity (do not alter EV).

B) Trading/Transaction Comparables (quick)
46) EV_Comps_EBITDA = EBITDA_t × sector_multiples[sector].ev_ebitda.
47) EV_Comps_Sales = Revenue_t × sector_multiples[sector].ev_sales.
48) transaction_comps_ev = median(EV_Comps_EBITDA, EV_Comps_Sales). Also compute the implied EV/EBITDA and EV/Sales for sanity.

C) Precedent Transactions (optional cross-check, no separate field in output)
49) EV_Precedent = EBITDA_t × precedent_multiples[sector].ev_ebitda (inform internal sanity only).

D) Asset-Based Valuation (NAV)
50) NAV_book = shareholders_equity_t (proxy if total assets/liabilities not given).
51) asset_based_ev = NAV_book (unless clear adjustments provided; then adjust modestly).

STEP 4 — BLENDING & EQUITY BRIDGE
52) Weights: DCF 0.60; Transaction Comps 0.25; Asset-based 0.15.
53) Final_EV = 0.60×EV_DCF + 0.25×transaction_comps_ev + 0.15×asset_based_ev.
54) Equity_Value = Final_EV + Cash_t − (Short_Term_Debt_t + Long_Term_Debt_t).

55) Valuation range (enterprise value):  
    low = min(EV_DCF, transaction_comps_ev, asset_based_ev)  
    high = max(EV_DCF, transaction_comps_ev, asset_based_ev)  
    mid = Final_EV

STEP 5 — SANITY & SCALE CHECKS (determine final scenario)
56) Using DCF EV from each scenario (A and B), compute implied EV/EBITDA_t.  
57) Apply sector deviation rule (± multiple_deviation). Choose the scenario per GLOBAL RULES.  
58) Report outputs from the chosen scenario only (absolute GEL). Do not include scenario diagnostics in the JSON.

OUTPUT — Return ONLY this JSON structure (values in absolute GEL; no extra fields, no prose outside JSON)
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
  "summary": "Based on a blended valuation using DCF, precedent transaction comps, and asset-based methods, the fair enterprise value of Company is approximately ₾. A realistic valuation range is  to . DCF carries the highest weight due to stable cash flows, while private SME deal data and asset values were used as cross-checks to ensure realism."
}

IMPORTANT
- Return ONLY the JSON structure above. Do not include any additional text, explanations, or markdown outside the JSON response.
- Use ONLY the INPUT and CONSTANTS provided (plus the explicit assumptions/guards). No external data.
"""
