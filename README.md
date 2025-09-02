# Financial Evaluation API

A simple Flask API for receiving and processing financial documents.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

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
  "status": "approved|conditional|rejected",
  "confidence": 0.85,
  "risk_level": "low|medium|high",
  "recommendation": "Proceed with investment",
  "estimated_return": "12.5%",
  "files_processed": 3,
  "uploaded_files": [
    {
      "filename": "document.pdf",
      "size": 1024000,
      "type": "pdf"
    }
  ]
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
