from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
from services.gemini_service import GeminiFinancialExtractor
from services.error_handler import ErrorHandler, handle_exceptions

logger = logging.getLogger(__name__)

loan_bp = Blueprint("loan", __name__)

gemini_extractor = None
try:
    gemini_extractor = GeminiFinancialExtractor()
except ValueError as e:
    print(f"Warning: Gemini not initialized - {e}")


@loan_bp.route("/loan/analyze", methods=["POST"])
@cross_origin()
@handle_exceptions
def analyze_loan():
    try:
        logger.info("Loan analysis endpoint called")

        if not gemini_extractor:
            logger.error("Gemini service not available")
            return ErrorHandler.api_error(
                "Loan analysis service not available. Please ensure GEMINI_API_KEY is configured."
            )

        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request is_json: {request.is_json}")

        if not request.is_json:
            logger.error("Request is not JSON")
            return ErrorHandler.validation_error("Request must be JSON")

        try:
            loan_data = request.get_json()
            logger.info(
                f"Received loan data keys: {list(loan_data.keys()) if loan_data else None}"
            )
        except Exception as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            return ErrorHandler.validation_error(f"Invalid JSON format: {str(e)}")

        if not loan_data:
            logger.error("No loan data provided")
            return ErrorHandler.validation_error("No loan data provided")

        # Extract required fields
        required_fields = ["financial_data", "valuation_data", "loan_request"]
        missing_fields = [field for field in required_fields if field not in loan_data]
        
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return ErrorHandler.validation_error(f"Missing required fields: {missing_fields}")

        # Analyze the loan request using Gemini
        try:
            logger.info("Starting loan analysis with Gemini")
            result = gemini_extractor.analyze_loan_request(
                loan_data["financial_data"],
                loan_data["valuation_data"], 
                loan_data["loan_request"]
            )
            logger.info("Loan analysis completed successfully")

            return jsonify({
                "success": True,
                "data": result,
                "message": "Loan analysis completed successfully"
            })

        except Exception as e:
            logger.error(f"Loan analysis failed: {str(e)}")
            return ErrorHandler.processing_error(f"Loan analysis failed: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error in loan analysis: {str(e)}")
        return ErrorHandler.processing_error(f"Unexpected error: {str(e)}")
