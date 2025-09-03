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
AI Valuation Prompt — Deterministic, Step-By-Step, With Zero-Input Resolution, Explicit FCFF & Tax, Simple Anchors (+ Optional Sensitivity)
ROLE
You are a valuation analyst replicating a plain Excel SME model.
Deterministic Mode ON: same input → same output. No randomness, no “smart” assumptions, no data fetching.

Follow the exact order below.

Perform every calculation manually.

Round to integers (0 decimals, absolute GEL) after each step.

Return ONLY the JSON structure at the end (format provided).

SIMPLE_MODE = TRUE by default; SENSITIVITY_MODE = FALSE (enable only when instructed).

INPUT (All figures are GEL in thousands → multiply by 1,000 before calculations)
CONSTANTS (Use exactly as written; no deviation)
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
  "sector_multiples": { "Retail": { "ev_ebitda": 6.5, "ev_sales": 0.9, "p_e": 12 } },
  "weights": { "dcf": 0.60, "transaction_comps": 0.25, "asset_based": 0.15 },
  "guards": {
    "anchor_band_pct": 0.15,
    "ev_sales_band": [0.7, 1.1],
    "ebitda_margin_clamp": [0.03, 0.18],
    "capex_pct_clamp": [0.01, 0.06],
    "da_pct_clamp": [0.01, 0.05],
    "days_clamp": { "dso": [5, 90], "dio": [15, 250], "dpo": [10, 180] }
  },
  "modes": { "SIMPLE_MODE": true, "SENSITIVITY_MODE": false },
  "fallback_defaults": {
    "dso_days": 25,
    "dio_days": 90,
    "dpo_days": 45,
    "ebitda_margin": 0.08,
    "capex_pct": 0.03,
    "da_pct": 0.025
  }
}
DETERMINISM PROTOCOL
Scale: Convert all inputs from GEL ‘000 to absolute GEL (×1,000) before any math.

No randomness/inference/fetching; constants and formulas only.

Rounding: Round after every sub-calculation to 0 decimals (integers).

Ordering: Follow the numbered order below.

Tie-breakers: If a choice is required, prefer lower WACC, then higher g, then lower EV (conservative).

ZERO-INPUT RESOLUTION RULES (apply before metrics; strictly ordered)
When any required input = 0 or missing, derive deterministically using the first applicable rule in each line. Round after deriving.

Priority Order of Derivation:

Z1. Revenue / COGS / Gross Profit
If two are known, derive the third:

Revenue = Gross_Profit + COGS

COGS = Revenue − Gross_Profit

Gross_Profit = Revenue − COGS

If only one known:

If Gross_Profit known and gross margin proxy available from prior year, use it to derive Revenue: Revenue = Gross_Profit / Gross_Margin_prior; then COGS = Revenue − Gross_Profit.

Else leave as is and proceed with provided numbers (no guessing).

Z2. EBIT / OpEx / Other Op / GP
Preferred identity: EBIT = (Revenue − COGS) − OpEx + Other_Op.

If EBIT = 0 and others known, derive EBIT from identity.

If OpEx = 0 and EBIT, GP, Other_Op known, OpEx = GP + Other_Op − EBIT.

If Other_Op = 0 and others known, Other_Op = EBIT − GP + OpEx.

Z3. D&A (Depreciation & Amortization)
If D&A = 0:

If PP&E_prev, Capex, PP&E_curr available:
D&A ≈ PP&E_prev + Capex − PP&E_curr (if negative → set to 0).

Else use fallback rate: D&A = Revenue × da_pct (clamp within da_pct_clamp).

Z4. Capex
Sign convention: cash outflow is negative.

If Capex = 0 and CFO and FCF available (company’s FCF definition):
Capex = FCF − CFO (likely negative).

Else use fallback rate: Capex = − (Revenue × capex_pct) (clamp within capex_pct_clamp, keep negative).

Z5. EBT / Tax Expense / Net Income
Core relations: EBT = NI + Tax_Expense; Tax_Expense = EBT − NI (if negative → 0).

If Tax_Expense = 0 and EBT, NI known: Tax_Expense = max(0, EBT − NI).

If EBT = 0 and NI, Tax_Expense known: EBT = NI + Tax_Expense.

If NI = 0 and EBT, Tax_Expense known: NI = EBT − Tax_Expense.

Z6. AR / Inventory / AP (Working Capital)
Using DSO/DIO/DPO with known Revenue and COGS:

If AR = 0:
AR = clamp_days(DSO) × Revenue / 365, where DSO = avg(DSO_22, DSO_23) if available, else fallback_defaults.dso_days, then clamp to days_clamp.dso.

If Inventory = 0:
Inventory = clamp_days(DIO) × COGS / 365, using same logic.

If AP = 0:
AP = clamp_days(DPO) × COGS / 365, using same logic.

Z7. ΔNWC
Primary (component method):
NWC_t = AR_t + Inventory_t − AP_t; ΔNWC = NWC_2023 − NWC_2022.

If component data insufficient but changes_in_working_capital provided: use it for ΔNWC.

If neither available: estimate with days drivers held flat (fallback days), compute NWC both years, then ΔNWC.

Z8. CFO Bridge (sanity only; not used for EV)
CFO_est ≈ NI + D&A − ΔNWC. If reported CFO present, note variance; do not overwrite FCFF path.

STEP-BY-STEP CALCULATION ORDER
STEP 0 — Scale & Normalize
0.1 Scale all inputs to absolute GEL.
0.2 Apply Zero-Input Resolution Rules (Z1–Z8) in order.

STEP 1 — Historical Core Metrics (2022 & 2023)
1.1 Integrity checks (tolerate ≤1% diff):

GP_check = Revenue − COGS vs Gross_Profit.

EBIT_check = GP − OpEx + Other_Op vs EBIT.

NI_check = EBT − Tax_Expense vs NI.
(Record flags; continue.)

1.2 EBITDA: EBITDA = EBIT + D&A.
1.3 Margins: Gross, EBITDA, EBIT, Net, and OpEx/Revenue.
1.4 Growth: YoY revenue growth; 2-year CAGR (2022→2023).

STEP 2 — Working Capital & Efficiency
2.1 Days: DSO = AR / Revenue × 365; DIO = Inventory / COGS × 365; DPO = AP / COGS × 365 (then clamp to days_clamp).
2.2 CCC: CCC = DSO + DIO − DPO.
2.3 NWC: NWC = AR + Inventory − AP.
2.4 ΔNWC: ΔNWC = NWC_2023 − NWC_2022.

STEP 3 — Capex & D&A Rates
3.1 Capex% = |Capex| / Revenue (clamp to capex_pct_clamp).
3.2 D&A% = D&A / Revenue (clamp to da_pct_clamp).
3.3 PP&E roll (note only): PP&E_t ≈ PP&E_(t−1) + Capex − D&A.

STEP 4 — Taxes (Deterministic)
4.1 Historical derived tax: Tax_Expense_hist = max(0, EBT − NI).
4.2 Effective rate: Eff_Tax = Tax_Expense_hist / max(EBT, 1).
4.3 Tax rate for modeling:

If Eff_Tax ∈ [5%, 35%] use it; else use normalized_tax_rate = 15%. Call the result Tax_Rate_used.

STEP 5 — Free Cash Flow (Explicit, Unlevered)
5.1 NOPAT: NOPAT = EBIT × (1 − Tax_Rate_used).
5.2 UFCF (historical): UFCF = NOPAT + D&A − Capex − ΔNWC.
5.3 (Optional) LFCF = NI + D&A − Capex − ΔNWC (not used for EV).

STEP 6 — Forecasts (Y+1…Y+5; deterministic)
6.1 Revenue growth path: exact 2-yr CAGR, linearly fade to terminal_growth_rate = 3.5% by Y+5.
6.2 Margins & rates:

EBITDA margin = median(EBITDA% 2022–2023), then clamp to ebitda_margin_clamp.

D&A% = average of 2022–2023, clamp to da_pct_clamp.

Capex% = average of 2022–2023 (absolute %), clamp to capex_pct_clamp.
6.3 Working capital drivers: hold DSO/DIO/DPO at 2-yr averages (post-clamp).

Each year, compute AR = DSO × Revenue / 365, Inventory = DIO × COGS / 365, AP = DPO × COGS / 365.

Then NWC_t and ΔNWC_t.
6.4 Profit & FCF each year:

EBITDA_t = Revenue_t × EBITDA_margin

D&A_t = Revenue_t × D&A%

EBIT_t = EBITDA_t − D&A_t

NOPAT_t = EBIT_t × (1 − Tax_Rate_used)

Capex_t = − Revenue_t × Capex% (negative)

UFCF_t = NOPAT_t + D&A_t − Capex_t − ΔNWC_t

Round each line annually in this order.

STEP 7 — Valuation (Simple Mode by default)
A) DCF (base, no sensitivity):
7.1 Terminal Value: TV = UFCF_Y5 × (1 + g) / (WACC − g) with WACC = 13.58%, g = 3.5%.
7.2 EV_DCF: Σ_{t=1..5} (UFCF_t / (1+WACC)^t) + TV/(1+WACC)^5.
(Compute discount factors, each PV, TV PV, then sum; round each step.)

B) Optional Simple Sensitivity (run only if SENSITIVITY_MODE = TRUE) — How to:

Keep forecasts fixed.

Define WACC_set = {0.1258, 0.1358, 0.1458}, g_set = {0.025, 0.035, 0.045}.

For each pair (WACC_i, g_j):

TV_ij = UFCF_Y5 × (1 + g_j) / (WACC_i − g_j)

EV_ij = Σ (UFCF_t / (1+WACC_i)^t) + TV_ij/(1+WACC_i)^5

ImpliedMultiple_ij = EV_ij / EBITDA_2023

Delta_ij = |ImpliedMultiple_ij − 6.5|

Round EV_ij, Multiple, Delta.

Select scenario with minimum Delta; tie-break: lower WACC, then higher g.

Replace EV_DCF with the selected EV_ij.

C) Transaction Comps (deterministic):
7.3 EV_EBITDA = EBITDA_2023 × 6.5
7.4 EV_Sales = Revenue_2023 × 0.9
7.5 EV_Comps = median(EV_EBITDA, EV_Sales) (if two medians, pick lower).

D) Asset-Based (NAV):
7.6 EV_NAV = Shareholders_Equity_2023 (book; no adjustments).

STEP 8 — Blending & Market Anchors (absurd-value guard)
8.1 Blended (pre-guard): EV_blended = 0.60×EV_DCF + 0.25×EV_Comps + 0.15×EV_NAV (round).
8.2 EV/EBITDA anchor:

Anchor_EV = EBITDA_2023 × 6.5

[A_low, A_high] = Anchor_EV × [1 − 0.15, 1 + 0.15]
8.3 EV/Sales band:

[S_low, S_high] = Revenue_2023 × [0.7, 1.1]
8.4 Clamp interval:

Clamp_Low = max(A_low, S_low)

Clamp_High = min(A_high, S_high)

If Clamp_Low > Clamp_High, use [A_low, A_high] only.
8.5 Final EV:

If EV_blended < Clamp_Low → EV_final = Clamp_Low

Else if EV_blended > Clamp_High → EV_final = Clamp_High

Else EV_final = EV_blended.

STEP 9 — Range & Reporting
9.1 Valuation range (reported):

low = min(EV_DCF, EV_Comps, EV_NAV)

high = max(EV_DCF, EV_Comps, EV_NAV)

mid = EV_final
(Round all three.)

9.2 (Optional notes, not changing numbers):

If EV_NAV > EV_DCF × 1.30, mention “asset-heavy” in summary.

If desired, compute Equity_estimate = EV_final − NetDebt_2023 and Implied P/E = Equity_estimate / NI_2023; if outside ~[10,14], just note in summary.

OUTPUT — Return ONLY this JSON (absolute GEL; integers)
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
  "summary": "Inputs treated as GEL in thousands and converted to absolute GEL. All missing zeros were deterministically derived using ordered rules (revenue/COGS/GP identities; EBIT from GP−OpEx+OtherOp; D&A from PP&E roll-forward else rate; Capex from FCF−CFO else rate; AR/Inventory/AP from DSO/DIO/DPO; ΔNWC from components else changes_in_working_capital). Taxes modeled as NOPAT=EBIT×(1−Tax_Rate_used) where Tax_Rate_used equals credible effective rate or 15% normalized. FCFF explicitly computed as NOPAT + D&A − Capex − ΔNWC. DCF uses fixed WACC=13.58% and g=3.5% (or optional simple sensitivity selecting the scenario closest to EV/EBITDA=6.5×). Final EV is blended and clamped within intersecting EV/EBITDA (±15%) and EV/Sales (0.7–1.1×) bands to avoid absurd values. Results are non-stochastic and identical on reruns."
}
"""
