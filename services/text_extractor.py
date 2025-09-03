import os
import docx
from PyPDF2 import PdfReader
import pandas as pd
import openpyxl

class TextExtractor:
    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        extractors = {
            '.pdf': TextExtractor._extract_from_pdf,
            '.docx': TextExtractor._extract_from_docx,
            '.txt': TextExtractor._extract_from_txt,
            '.xlsx': TextExtractor._extract_from_excel,
            '.xls': TextExtractor._extract_from_excel
        }
        
        if ext not in extractors:
            raise ValueError(f"Unsupported file type: {ext}")
        
        try:
            text = extractors[ext](file_path)
            return TextExtractor._clean_text(text)
        except Exception as e:
            raise RuntimeError(f"Error extracting text from {ext} file: {str(e)}")
    
    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        text = ""
        reader = PdfReader(file_path)
        
        if len(reader.pages) == 0:
            raise ValueError("PDF file contains no pages")
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        if not text.strip():
            raise ValueError("No text could be extracted from PDF")
        
        return text
    
    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        text = ""
        doc = docx.Document(file_path)
        
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"
        
        if not text.strip():
            raise ValueError("No text could be extracted from DOCX file")
        
        return text
    
    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        
        if not text.strip():
            raise ValueError("Text file is empty")
        
        return text
    
    @staticmethod
    def _extract_from_excel(file_path: str) -> str:
        try:
            # Read all sheets from the Excel file
            excel_file = pd.ExcelFile(file_path)
            extracted_text = ""
            
            for sheet_name in excel_file.sheet_names:
                # Read the sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Add sheet header
                extracted_text += f"\n--- SHEET: {sheet_name} ---\n\n"
                
                # Convert DataFrame to readable text format
                if not df.empty:
                    # Include column headers
                    headers = ' | '.join(str(col) for col in df.columns if pd.notna(col))
                    if headers.strip():
                        extracted_text += f"Columns: {headers}\n\n"
                    
                    # Process each row
                    for index, row in df.iterrows():
                        row_text = []
                        for col_name, value in row.items():
                            if pd.notna(value) and str(value).strip():
                                # Format as "Column: Value"
                                row_text.append(f"{col_name}: {value}")
                        
                        if row_text:
                            extracted_text += ' | '.join(row_text) + "\n"
                    
                    extracted_text += "\n"
                else:
                    extracted_text += "Sheet is empty\n\n"
            
            if not extracted_text.strip():
                raise ValueError("No data could be extracted from Excel file")
            
            return extracted_text
            
        except Exception as e:
            raise RuntimeError(f"Error reading Excel file: {str(e)}")
    
    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        
        # Remove excessive whitespace while preserving structure
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = ' '.join(line.split())
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
