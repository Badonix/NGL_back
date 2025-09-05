import os
import re
import uuid
from config import Config


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

        name_part, ext = os.path.splitext(filename)
        ext = ext.lower()

        if not name_part and ext:
            timestamp = str(uuid.uuid4())[:8]
            safe_name = f"file_{timestamp}"
            return safe_name + ext

        dangerous_chars = r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]'
        safe_name = re.sub(dangerous_chars, "", name_part)

        safe_name = safe_name.strip(". ")

        if not safe_name or len(safe_name) < 1:
            timestamp = str(uuid.uuid4())[:8]
            safe_name = f"file_{timestamp}"

        if not ext:
            ext = ".txt"

        if len(safe_name) > 200:
            safe_name = safe_name[:200]

        return safe_name + ext

    @classmethod
    def validate_file(cls, file):
        if not file or file.filename == "":
            raise ValueError("No file uploaded or empty filename")

        original_filename = file.filename

        file_ext = os.path.splitext(original_filename)[1].lower()
        if file_ext not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {file_ext}. Allowed: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )

        safe_filename = cls._unicode_safe_filename(original_filename)
        if not safe_filename:
            raise ValueError("Invalid filename")

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
            "size": os.path.getsize(filepath),
            "exists": True,
            "extension": os.path.splitext(filepath)[1].lower(),
        }
