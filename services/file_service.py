import os
from werkzeug.utils import secure_filename
from config import Config
from .error_handler import ErrorHandler

class FileService:
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
    
    @classmethod
    def validate_file(cls, file):
        if not file or file.filename == "":
            raise ValueError("No file uploaded or empty filename")
        
        filename = secure_filename(file.filename)
        if not filename:
            raise ValueError("Invalid filename")
        
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {file_ext}. Allowed: {', '.join(cls.ALLOWED_EXTENSIONS)}")
        
        return filename
    
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
