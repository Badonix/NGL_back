# Multiple Files Support

## Overview

The evaluation endpoint now supports uploading and processing **multiple files** in a single request. This allows users to upload related financial documents (e.g., Income Statement + Balance Sheet + Cash Flow Statement) and get a comprehensive analysis from all documents combined.

## Implementation Details

### 1. **Backend Changes**

#### **Route Handler** (`routes/evaluation.py`)

- **Before**: Processed single file with `request.files["files"]`
- **After**: Processes multiple files with `request.files.getlist("files")`

```python
# Get all files with the same field name
uploaded_files = request.files.getlist("files")

# Process each file
for file in uploaded_files:
    filepath, filename = FileService.save_uploaded_file(file)
    extracted_text = TextExtractor.extract_text_from_file(filepath)
    # Combine text with file separators
    combined_text += f"\n\n--- FILE: {filename} ---\n\n{extracted_text}"
```

#### **Text Combination Strategy**

Files are combined with clear separators:

```
--- FILE: income_statement.pdf ---

[Content of income statement]

--- FILE: balance_sheet.pdf ---

[Content of balance sheet]

--- FILE: cash_flow.pdf ---

[Content of cash flow statement]
```

#### **Response Enhancement** (`services/response_formatter.py`)

New response fields:

- `file_count`: Number of files processed
- `processed_files`: Array of filenames
- `filename`: Summary string with all filenames

### 2. **Frontend Compatibility**

The frontend was already sending multiple files correctly:

```typescript
files.forEach((uploadedFile) => {
  formData.append("files", uploadedFile.file);
});
```

## Usage Examples

### **Single File (Backward Compatible)**

```bash
curl -X POST http://localhost:5000/evaluate \
  -F "files=@financial_statement.pdf"
```

### **Multiple Files**

```bash
curl -X POST http://localhost:5000/evaluate \
  -F "files=@income_statement.pdf" \
  -F "files=@balance_sheet.pdf" \
  -F "files=@cash_flow.pdf"
```

### **Frontend JavaScript**

```javascript
const formData = new FormData();
files.forEach((file) => {
  formData.append("files", file);
});

fetch("/evaluate", {
  method: "POST",
  body: formData,
});
```

## Response Format

### **Success Response**

```json
{
  "message": "success",
  "filename": "3 files: income_statement.pdf, balance_sheet.pdf, cash_flow.pdf",
  "length": 15420,
  "file_count": 3,
  "processed_files": [
    "income_statement.pdf",
    "balance_sheet.pdf",
    "cash_flow.pdf"
  ],
  "success": true,
  "data": {
    "financial_analysis": {
      "data": {
        "financial_analysis": { ... },
        "summerized_data": { ... }
      },
      "success": true
    }
  },
  "pdf": {
    "available": true,
    "filename": "financial_summary_20250103_143022.pdf",
    "url": "/pdfs/financial_summary_20250103_143022.pdf"
  }
}
```

## AI Processing

### **Gemini Analysis**

The AI receives the combined text from all files and can:

- ✅ Cross-reference data between documents
- ✅ Identify complementary information
- ✅ Detect inconsistencies across files
- ✅ Provide comprehensive analysis from multiple sources

### **Example Combined Input**

```
--- FILE: 2023_income_statement.pdf ---

Revenue: $1,000,000
COGS: $600,000
...

--- FILE: 2023_balance_sheet.pdf ---

Total Assets: $500,000
Cash: $50,000
...

--- FILE: 2023_cash_flow.pdf ---

Operating Cash Flow: $180,000
...
```

## Benefits

### ✅ **Comprehensive Analysis**

- Process complete financial statement sets in one request
- Cross-document validation and analysis
- More accurate financial insights

### ✅ **Improved User Experience**

- Upload related documents together
- Single analysis covers all documents
- Reduced API calls and processing time

### ✅ **Better Data Quality**

- AI can correlate information across documents
- Detect and resolve inconsistencies
- More complete financial picture

### ✅ **Backward Compatibility**

- Single file uploads still work exactly as before
- No breaking changes to existing functionality
- Gradual migration path for users

## Error Handling

### **File Validation**

- Each file is validated individually
- Invalid files are skipped with warnings
- At least one valid file required for processing

### **Processing Errors**

- Errors in individual files don't fail entire request
- Detailed error reporting per file
- Graceful degradation

### **Cleanup**

- All uploaded files cleaned up after processing
- Even if processing fails, temporary files removed
- No file system pollution

## Technical Considerations

### **Memory Usage**

- Combined text stored in memory during processing
- Large file sets may require memory management
- Consider streaming for very large document sets

### **Processing Time**

- Multiple files increase processing time
- AI analysis time scales with combined content length
- Timeout handling for large document sets

### **File Limits**

- Current: No explicit limit on file count
- Recommendation: Implement reasonable limits (e.g., 10 files max)
- Consider total size limits for practical usage

## Testing

### **Test Script**

Run `test_multiple_files.py` to verify functionality:

```bash
python test_multiple_files.py
```

### **Test Cases**

- ✅ Single file (backward compatibility)
- ✅ Multiple files (2-5 files)
- ✅ Mixed file types (PDF + DOCX + TXT)
- ✅ Empty file handling
- ✅ Invalid file type rejection
- ✅ Large file sets

The multiple file support provides a more robust and user-friendly financial analysis experience while maintaining full backward compatibility.
