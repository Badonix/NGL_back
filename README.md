# Financial Evaluation API

A Flask API for receiving and processing financial documents with AI-powered analysis using Google Gemini 2.5 Pro.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure Gemini API:

Create a `.env` file in the `back/` directory:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API key from: https://makersuite.google.com/app/apikey

3. Run the application:

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## Endpoints

### POST /evaluate

Upload files for financial evaluation.

**Supported file types:**

- PDF (.pdf)
- Excel (.xlsx, .xls)
- Word (.docx, .doc)

**Request:**

- Method: POST
- Content-Type: multipart/form-data
- Body: files (multiple files allowed)

**Response:**

```json
{
  "message": "success",
  "filename": "document.pdf",
  "preview": "First 500 characters of extracted text...",
  "length": 15000,
  "financial_analysis": {
    "success": true,
    "data": {
      "company_info": {
        "name": "Example Corp",
        "industry": "Technology",
        "description": "Software company"
      },
      "financial_metrics": {
        "revenue": {
          "current": 1000000,
          "previous": 800000,
          "currency": "USD"
        },
        "net_income": {
          "current": 150000,
          "previous": 120000,
          "currency": "USD"
        }
      },
      "ratios": {
        "profit_margin": 0.15,
        "roe": 0.12
      },
      "risk_factors": ["Market competition", "Regulatory changes"],
      "investment_highlights": ["Strong revenue growth", "Market leadership"]
    }
  },
  "investment_recommendation": {
    "success": true,
    "recommendation": {
      "recommendation": "Buy",
      "confidence": "High",
      "strengths": ["Strong financials", "Growth potential"],
      "weaknesses": ["Market volatility"],
      "risk_level": "Medium",
      "summary": "Strong buy recommendation based on solid fundamentals"
    }
  }
}
```

### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "message": "Financial evaluation API is running"
}
```

## File Upload Example

```bash
curl -X POST -F "files=@document1.pdf" -F "files=@spreadsheet.xlsx" http://localhost:5000/evaluate
```
