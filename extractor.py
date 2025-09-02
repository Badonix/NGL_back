# extractor.py
import os
import docx
from PyPDF2 import PdfReader

def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from PDF, DOCX, or TXT files.
    Returns clean string text.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    text = ""

    try:
        if ext == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        elif ext == ".docx":
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n"

        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

        else:
            raise ValueError(f"Unsupported file type: {ext}")

    except Exception as e:
        return f"Error extracting text: {e}"

    # clean: remove duplicate spaces, line breaks
    text = " ".join(text.split())
    return text
