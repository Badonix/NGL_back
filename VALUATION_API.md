# Valuation API Documentation

## Overview

The valuation API provides AI-powered company valuation analysis using professional corporate valuation methodologies.

## Endpoints

### POST `/valuation/evaluate`

Performs comprehensive company valuation analysis using three methodologies:

- Discounted Cash Flow (DCF)
- Precedent Transaction Comparables
- Asset-Based Valuation (ABV)

#### Request

**Content-Type:** `application/json`

**Required Body Structure:**

```json
{
  "income_statement": {
    "revenue_sales": { "2022": 683795, "2023": 700075 },
    "cogs": { "2022": 523940, "2023": 529105 },
    "operating_expenses": { "2022": 131218, "2023": 143983 },
    "operating_profit_ebit": { "2022": 29798, "2023": 34473 },
    "interest_expense": { "2022": 8768, "2023": 8078 },
    "interest_income": { "2022": 16706, "2023": 4562 },
    "net_income": { "2022": 51407, "2023": 35964 }
  },
  "balance_sheet": {
    "cash_equivalents": { "2022": 48586, "2023": 17623 },
    "accounts_receivable": { "2022": 36473, "2023": 78674 },
    "inventory": { "2022": 256002, "2023": 243959 },
    "ppe": { "2022": 67605, "2023": 71747 },
    "accounts_payable": { "2022": 186078, "2023": 163061 },
    "shareholders_equity": { "2022": 305119, "2023": 326417 }
  },
  "cash_flow_statement": {
    "cash_flow_from_operations": { "2022": 26952, "2023": -2917 },
    "capital_expenditures": { "2022": -9171, "2023": -13084 },
    "taxes_paid": { "2022": 34112, "2023": 40093 },
    "interest_paid": { "2022": 8427, "2023": 6895 }
  }
}
```

#### Response

**Success Response (200):**

```json
{
  "success": true,
  "message": "Valuation analysis completed successfully",
  "data": {
    "company": "Company XYZ",
    "currency": "GEL",
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
    "summary": "Based on a blended valuation using DCF, precedent transaction comps, and asset-based methods, the fair enterprise value of Company XYZ is approximately ₾1.50M..."
  }
}
```

**Error Response (400/500):**

```json
{
  "error": "Error message",
  "error_type": "validation_error|processing_error|api_error",
  "success": false
}
```

### GET `/valuation/health`

Health check endpoint for the valuation service.

#### Response

```json
{
  "service": "valuation",
  "status": "healthy|unavailable",
  "gemini_configured": true
}
```

## Usage Example

```bash
curl -X POST http://localhost:5000/valuation/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "income_statement": {
      "revenue_sales": {"2022": 683795, "2023": 700075},
      "net_income": {"2022": 51407, "2023": 35964}
    },
    "balance_sheet": {
      "cash_equivalents": {"2022": 48586, "2023": 17623},
      "shareholders_equity": {"2022": 305119, "2023": 326417}
    },
    "cash_flow_statement": {
      "cash_flow_from_operations": {"2022": 26952, "2023": -2917}
    }
  }'
```

## Error Handling

The API includes comprehensive error handling for:

- Missing required financial data sections
- Invalid JSON format
- AI processing errors
- Service unavailability (when Gemini API key not configured)

All errors follow a consistent format with `error`, `error_type`, and `success` fields.
