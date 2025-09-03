from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
from services.valuation_service import ValuationService
from services.error_handler import ErrorHandler, handle_exceptions

logger = logging.getLogger(__name__)

valuation_bp = Blueprint('valuation', __name__)

valuation_service = None
try:
    valuation_service = ValuationService()
except ValueError as e:
    print(f"Warning: Valuation service not initialized - {e}")

@valuation_bp.route("/valuation/evaluate", methods=["POST"])
@cross_origin()
def evaluate_valuation():
    try:
        logger.info("Valuation endpoint called")
        
        if not valuation_service:
            logger.error("Valuation service not available")
            return ErrorHandler.api_error("Valuation service not available. Please ensure GEMINI_API_KEY is configured.")
        
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request is_json: {request.is_json}")
        
        if not request.is_json:
            logger.error("Request is not JSON")
            return ErrorHandler.validation_error("Request must be JSON")
        
        try:
            financial_data = request.get_json()
            logger.info(f"Received financial data keys: {list(financial_data.keys()) if financial_data else None}")
        except Exception as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            return ErrorHandler.validation_error(f"Invalid JSON format: {str(e)}")
        
        if not financial_data:
            logger.error("No financial data provided")
            return ErrorHandler.validation_error("No financial data provided")
        
        # Validate that we have the required financial statement data
        required_sections = ['income_statement', 'balance_sheet', 'cash_flow_statement']
        missing_sections = [section for section in required_sections if section not in financial_data]
        
        if missing_sections:
            logger.error(f"Missing required sections: {missing_sections}")
            return ErrorHandler.validation_error(f"Missing required financial data sections: {', '.join(missing_sections)}")
        
        logger.info("Starting valuation analysis")
        valuation_result = valuation_service.perform_valuation(financial_data)
        
        if valuation_result.get("success"):
            logger.info("Valuation analysis completed successfully")
            return jsonify({
                "success": True,
                "message": "Valuation analysis completed successfully",
                "data": valuation_result.get("data")
            }), 200
        else:
            logger.error(f"Valuation analysis failed: {valuation_result.get('error')}")
            return ErrorHandler.processing_error(valuation_result.get("error", "Valuation analysis failed"))
            
    except Exception as e:
        logger.error(f"Unexpected error in valuation endpoint: {str(e)}", exc_info=True)
        return ErrorHandler.processing_error(f"Valuation processing error: {str(e)}")

@valuation_bp.route("/valuation/test", methods=["POST"])
@cross_origin()
def test_endpoint():
    try:
        logger.info("Test endpoint called")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request is_json: {request.is_json}")
        
        if request.is_json:
            data = request.get_json()
            logger.info(f"JSON data received: {data}")
            return jsonify({"success": True, "received": data}), 200
        else:
            return jsonify({"error": "Request is not JSON", "content_type": request.content_type}), 400
            
    except Exception as e:
        logger.error(f"Test endpoint error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@valuation_bp.route("/valuation/health", methods=["GET"])
def valuation_health():
    return jsonify({
        "service": "valuation",
        "status": "healthy" if valuation_service else "unavailable",
        "gemini_configured": valuation_service is not None
    }), 200
