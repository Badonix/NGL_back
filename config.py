import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    UPLOAD_FOLDER = "uploads"
    PUBLIC_FOLDER = "public"
    PDF_FOLDER = f"{PUBLIC_FOLDER}/pdfs"

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    @classmethod
    def ensure_directories(cls):
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.PUBLIC_FOLDER, exist_ok=True)
        os.makedirs(cls.PDF_FOLDER, exist_ok=True)
