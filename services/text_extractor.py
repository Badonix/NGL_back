import os
import docx
from PyPDF2 import PdfReader

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
            '.txt': TextExtractor._extract_from_txt
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
