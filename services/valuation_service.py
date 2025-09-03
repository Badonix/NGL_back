import google.generativeai as genai
import json
from config import Config


class ValuationService:
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

        self.generation_config = {
            "max_output_tokens": 8192,
            "temperature": 0.2,
        }

        self.valuation_prompt = self._get_valuation_prompt()

    def perform_valuation(self, financial_data):
        try:
            full_prompt = (
                self.valuation_prompt
                + "\n\nFinancial Data JSON:\n"
                + json.dumps(financial_data, indent=2)
            )

            response = self.model.generate_content(
                full_prompt, generation_config=self.generation_config
            )

            if not response.text:
                raise ValueError("No response generated from Gemini")

            valuation_result = self._parse_response(response.text)

            return {"success": True, "data": valuation_result}

        except Exception as e:
            return {"success": False, "error": f"Valuation analysis error: {str(e)}"}

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
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}")
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = response_text[start_idx : end_idx + 1]
                else:
                    json_text = response_text

            json_text = json_text.replace("\\n", "\n").replace('\\"', '"')

            return json.loads(json_text)

        except json.JSONDecodeError as e:
            # If JSON parsing fails, return the raw response with error info
            return {
                "error": f"Failed to parse JSON response: {str(e)}",
                "raw_response": (response_text),
            }

    def _get_valuation_prompt(self):
        return """
AI Valuation Prompt — Deterministic, Simple-Mode, Scale-Safe, With Explicit FCF & Tax Logic (+ Simple Sensitivity)
ROLE
You are a valuation analyst replicating a plain Excel SME model.
Deterministic Mode ON: same input → same output. No randomness, no “smart” assumptions, no fetching.

Do every calculation manually in this exact order.

Round to integers (0 decimals, absolute GEL) after each step.

Return ONLY the JSON structure at the end (format provided).

Simple Mode = TRUE (skip sensitivity grid by default). You may run the grid only if SENSITIVITY_MODE = TRUE.

INPUT (All figures are GEL in thousands → multiply by 1,000 first)
Use this exact structure (numbers shown are example inputs):

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
Unit rule: Treat inputs as GEL thousands. Convert to absolute GEL at the start and keep absolute GEL everywhere.

CONSTANTS (Do not change)
{
  "constants": {
    "risk_free_rate": 0.0758,
    "equity_risk_premium": 0.05,
    "country_risk_premium": 0.04,
    "terminal_growth_rate": 0.035,
    "beta": 1.0,
    "normalized_tax_rate": 0.15,
    "wacc": 0.1358
  },
  "sector_multiples": {
    "Retail": { "ev_ebitda": 6.5, "ev_sales": 0.9, "p_e": 12 }
  },
  "weights": { "dcf": 0.60, "transaction_comps": 0.25, "asset_based": 0.15 },
  "guards": {
    "ev_ebitda_band": [5.5, 7.5],
    "ev_sales_band": [0.7, 1.1],
    "anchor_band_pct": 0.15
  },
  "modes": {
    "SIMPLE_MODE": true,
    "SENSITIVITY_MODE": false
  }
}
STEP 1 — BASIC CHECKS (absolute GEL)
Scale: multiply every input by 1,000.

Integrity (tolerate ≤1%):

GP_check = Revenue − COGS ≈ Gross_Profit

EBIT_check = Gross_Profit − OpEx + Other_Op ≈ EBIT

NI_check = EBT − Tax_Expense ≈ Net_Income

STEP 2 — TAXES (explicit & deterministic)
Goal: avoid guessing public tax data; compute cleanly and consistently.

Historical tax expense (derived):
Tax_Expense_hist = max(0, EBT − Net_Income) (if negative, set to 0).

Historical effective rate:
Eff_Tax_Rate_hist = Tax_Expense_hist / max(EBT, 1)

Tax rate for NOPAT, WACC shield, and forecasts:
If Eff_Tax_Rate_hist is < 5% or > 35%, set Tax_Rate_used = normalized_tax_rate (15%);
else use Tax_Rate_used = Eff_Tax_Rate_hist (rounded).

Cash taxes (historical, for info only):
If taxes_paid provided, use it; otherwise approximate with Tax_Expense_hist.
(Do not use cash taxes in UFCF; UFCF uses NOPAT path.)

STEP 3 — CORE PROFITABILITY & MARGINS
EBITDA = EBIT + D&A

Margins (each year):

Gross_Margin = GP / Revenue

EBITDA_Margin = EBITDA / Revenue

EBIT_Margin = EBIT / Revenue

Net_Margin = NI / Revenue

Revenue Growth (2023 vs 2022) and 2-yr CAGR.

STEP 4 — WORKING CAPITAL & EFFICIENCY
DSO = AR / Revenue × 365

DIO = Inventory / COGS × 365

DPO = AP / COGS × 365

CCC = DSO + DIO − DPO

NWC = AR + Inventory − AP

ΔNWC = NWC_2023 − NWC_2022

STEP 5 — CAPEX, D&A, PP&E SANITY
Capex% = |Capex| / Revenue

D&A% = D&A / Revenue

PP&E roll-forward check (note only):
PP&E_t ≈ PP&E_(t−1) + Capex − D&A (flag internally if large gap)

STEP 6 — FREE CASH FLOW (EXPLICIT)
Use Unlevered FCF (UFCF) based on NOPAT — no financing noise.

NOPAT = EBIT × (1 − Tax_Rate_used)

Unlevered FCF (historical & forecast):
UFCF = NOPAT + D&A − Capex − ΔNWC
(All four terms must be computed for the same period; round each term and UFCF.)

(Optional, not used in EV): Levered FCF (LFCF)
LFCF = Net_Income + D&A − Capex − ΔNWC (do not use for EV)

STEP 7 — FORECASTS (Y+1…Y+5; Simple & fixed)
Revenue growth: exact 2-yr CAGR (2022→2023), linearly fade to terminal_growth_rate (3.5%) by Y+5.

EBITDA margin: 2-yr median (fixed).

D&A% and Capex%: 2-yr averages (fixed).

Working capital: hold DSO/DIO/DPO at 2-yr averages → derive NWC each year; ΔNWC is YoY change.

EBIT each year: EBIT = EBITDA − D&A.

NOPAT each year: EBIT × (1 − Tax_Rate_used).

UFCF each year: NOPAT + D&A − Capex − ΔNWC.

Round every line annually.

STEP 8 — VALUATION (Simple Mode by default)
A) DCF (base, no sensitivity)
Use fixed WACC = 13.58%, g = 3.5%.

Terminal Value:
TV = UFCF_Y5 × (1 + g) / (WACC − g)

DCF EV:
EV_DCF = Σ[UFCF_t / (1+WACC)^t] for t=1..5 + TV / (1+WACC)^5

Round discount factors, each PV, TV PV, and EV_DCF.

If SENSITIVITY_MODE = TRUE: run the Simple Sensitivity below and replace EV_DCF with the selected scenario’s EV.

B) Transaction Comps (deterministic)
EV_EBITDA = EBITDA_2023 × 6.5

EV_Sales = Revenue_2023 × 0.9

EV_Comps = median(EV_EBITDA, EV_Sales) (if two medians, take the lower)

C) Asset-Based (NAV, simple)
EV_NAV = Shareholders_Equity_2023 (book; no adjustments)

STEP 9 — BLENDING + ABSURD-VALUE GUARDS
Blended EV (pre-guard):
EV_blended = 0.60 × EV_DCF + 0.25 × EV_Comps + 0.15 × EV_NAV (round)

Anchor bands (to avoid absurd values):

EV/EBITDA anchor: Anchor_EBITDA = EBITDA_2023 × 6.5
→ [Low_A, High_A] = Anchor_EBITDA × [1 − 0.15, 1 + 0.15]

EV/Sales band: EV_Sales_band = Revenue_2023 × [0.7, 1.1]

Intersection guard:
[Clamp_Low, Clamp_High] = [ max(Low_A, 0.7×Revenue), min(High_A, 1.1×Revenue) ]
If Clamp_Low > Clamp_High, use [Low_A, High_A] only.

Final EV (clamped):

If EV_blended < Clamp_Low → EV_final = Clamp_Low

Else if EV_blended > Clamp_High → EV_final = Clamp_High

Else EV_final = EV_blended

STEP 10 — RANGE & OUTPUT
Valuation range:
low = min(EV_DCF, EV_Comps, EV_NAV)
high = max(EV_DCF, EV_Comps, EV_NAV)
mid = EV_final

All numbers must be in absolute GEL (integers).

Return ONLY this JSON structure:

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
  "summary": "Inputs treated as GEL in thousands and converted to absolute GEL. Taxes derived deterministically (Tax_Expense = max(0, EBT − NI); effective rate validated; 15% normalized rate used for NOPAT and WACC). Unlevered FCF computed explicitly as NOPAT + D&A − Capex − ΔNWC. Simple Mode uses fixed WACC=13.58% and g=3.5% for DCF, median of EV/EBITDA and EV/Sales for comps, and book equity for NAV. Final EV is blended and clamped within intersecting EV/EBITDA and EV/Sales bands (±15% around sector anchor; 0.7–1.1× revenue) to prevent absurd values. Optional Simple Sensitivity can be run deterministically as described; results are fully deterministic and identical on reruns."
}
OPTIONAL SIMPLE SENSITIVITY (EXPLAINED & DETERMINISTIC)
Enable by setting "SENSITIVITY_MODE": true. This is a lite, easy-to-compute grid.

What to vary
WACC set (3 points): {WACC − 1%, WACC, WACC + 1%} → {0.1258, 0.1358, 0.1458}

Terminal growth set (3 points): {g − 1%, g, g + 1%} → {0.025, 0.035, 0.045}

(If you want an even simpler version, use a 2×2 grid: {WACC, WACC+1%} × {g, g+1%} with the same selection rule below.)

How to do it (step-by-step)
Hold forecasts fixed. Do not recompute revenue/margins/ΔNWC; only change discount rates and TV formula.

For each (WACC_i, g_j) pair:

Compute TV = UFCF_Y5 × (1 + g_j) / (WACC_i − g_j)

Compute EV_ij = Σ UFCF_t / (1 + WACC_i)^t + TV / (1 + WACC_i)^5

Compute ImpliedMultiple_ij = EV_ij / EBITDA_2023

Compute Delta_ij = |ImpliedMultiple_ij − 6.5|

Round EV_ij, ImpliedMultiple_ij, and Delta_ij to integers (EV) and two decimals (multiple) if desired, then round EV to integer for use.

Select the scenario with minimum Delta_ij.

Tie-breakers (deterministic): pick lower WACC; if still tied, pick higher g.

Replace base EV_DCF with this selected EV_ij.

Continue with blending and clamping exactly as in Steps 9–10.

Why this works: it anchors DCF to sector reality (EV/EBITDA≈6.5×) without changing your clean, deterministic cash-flow build, and it keeps runtime extremely simple.

Notes for stability

Keep SIMPLE_MODE = true by default; turn on sensitivity only when needed.

Always round after each step to avoid drift.

Keep all constants fixed; never fetch or infer.

If results look off, check scale (×1,000), tax logic, and ΔNWC sign.
"""
