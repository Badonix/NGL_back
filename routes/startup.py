from flask import Blueprint, request, jsonify
from services.gemini_service import GeminiFinancialExtractor
from services.response_formatter import ResponseFormatter
from services.error_handler import ErrorHandler, handle_exceptions
import json

startup_bp = Blueprint("startup", __name__)

# Initialize Gemini service
gemini_extractor = GeminiFinancialExtractor()

@startup_bp.route("/startup-analyze", methods=["POST"])
@handle_exceptions
def analyze_startup():
    """
    Analyze startup description using Gemini AI for valuation, competitive analysis,
    and investor discovery
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return ErrorHandler.validation_error("Request body is required")
        
        startup_description = data.get("startup_description", "").strip()
        flags = data.get("flags", {})
        
        if not startup_description:
            return ErrorHandler.validation_error("Startup description is required")
        
        # Analyze startup using Gemini
        if gemini_extractor:
            analysis_result = gemini_extractor.analyze_startup(
                startup_description, 
                flags
            )
        else:
            analysis_result = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
            }
        
        return ResponseFormatter.format_startup_response(analysis_result)
        
    except Exception as e:
        return ErrorHandler.processing_error(str(e))
