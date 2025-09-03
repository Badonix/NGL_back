from flask import Blueprint, request
from services.file_service import FileService
from services.text_extractor import TextExtractor
from services.gemini_service import GeminiFinancialExtractor
from services.response_formatter import ResponseFormatter
from services.error_handler import ErrorHandler, handle_exceptions

evaluation_bp = Blueprint('evaluation', __name__)

gemini_extractor = None
try:
    gemini_extractor = GeminiFinancialExtractor()
except ValueError as e:
    print(f"Warning: Gemini not initialized - {e}")

@evaluation_bp.route("/evaluate", methods=["POST"])
@handle_exceptions
def evaluate():
    if "files" not in request.files:
        return ErrorHandler.validation_error("No file uploaded")
    
    file = request.files["files"]
    
    try:
        filepath, filename = FileService.save_uploaded_file(file)
        
        extracted_text = TextExtractor.extract_text_from_file(filepath)
        
        if gemini_extractor:
            financial_analysis = gemini_extractor.extract_financial_data(extracted_text)
        else:
            financial_analysis = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
            }
        
        return ResponseFormatter.format_evaluation_response(
            filename=filename,
            text_length=len(extracted_text),
            financial_analysis=financial_analysis
        )
        
    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        try:
            FileService.cleanup_file(filepath)
        except:
            pass
