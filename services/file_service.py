import os
import re
import uuid
from werkzeug.utils import secure_filename
from config import Config
from .error_handler import ErrorHandler

class FileService:
    ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".pdf", ".docx", ".doc", ".txt"}
    
    @classmethod
    def _unicode_safe_filename(cls, filename):
        """
        Create a safe filename that preserves Unicode characters while removing dangerous ones.
        Falls back to UUID-based naming if the filename becomes too problematic.
        """
        if not filename:
            return None
        
        # Get the original extension first
        name_part, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        # Special handling for filenames that are just extensions (like ".pdf")
        if not name_part and ext:
            timestamp = str(uuid.uuid4())[:8]
            safe_name = f"file_{timestamp}"
            return safe_name + ext
        
        # Remove dangerous characters but preserve Unicode letters and numbers
        # Remove: path separators, control characters, and reserved characters
        dangerous_chars = r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]'
        safe_name = re.sub(dangerous_chars, '', name_part)
        
        # Remove leading/trailing dots and spaces
        safe_name = safe_name.strip('. ')
        
        # If name becomes empty or too short, use UUID with timestamp
        if not safe_name or len(safe_name) < 1:
            timestamp = str(uuid.uuid4())[:8]
            safe_name = f"file_{timestamp}"
        
        # Handle edge case where extension is missing
        if not ext:
            ext = ".txt"  # Default extension
        
        # Limit length to avoid filesystem issues
        if len(safe_name) > 200:
            safe_name = safe_name[:200]
        
        return safe_name + ext
    
    @classmethod
    def validate_file(cls, file):
        if not file or file.filename == "":
            raise ValueError("No file uploaded or empty filename")
        
        original_filename = file.filename
        
        # First check if the extension is valid using the original filename
        file_ext = os.path.splitext(original_filename)[1].lower()
        if file_ext not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {file_ext}. Allowed: {', '.join(cls.ALLOWED_EXTENSIONS)}")
        
        # Create a safe filename that preserves Unicode characters
        safe_filename = cls._unicode_safe_filename(original_filename)
        if not safe_filename:
            raise ValueError("Invalid filename")
        
        # Double-check extension is preserved
        if not safe_filename.lower().endswith(file_ext):
            safe_filename = safe_filename + file_ext
        
        return safe_filename
    
    @classmethod
    def save_uploaded_file(cls, file):
        filename = cls.validate_file(file)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        
        try:
            file.save(filepath)
            return filepath, filename
        except Exception as e:
            raise IOError(f"Failed to save file: {str(e)}")
    
    @classmethod
    def cleanup_file(cls, filepath):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Warning: Could not clean up file {filepath}: {e}")
    
    @classmethod
    def get_file_info(cls, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        return {
            'size': os.path.getsize(filepath),
            'exists': True,
            'extension': os.path.splitext(filepath)[1].lower()
        }
