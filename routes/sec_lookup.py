from flask import Blueprint, request, jsonify
from services.sec_lookup import sec_lookup_service
from services.error_handler import ErrorHandler
from services.response_formatter import ResponseFormatter

sec_lookup_bp = Blueprint('sec_lookup', __name__)

@sec_lookup_bp.route('/lookup-company', methods=['POST'])
def lookup_company():
    """
    Look up company by name/ticker via SEC data
    
    Request body:
    {
        "company_name": str,
        "threshold": int (optional, default 75)
    }
    
    Response:
    {
        "success": bool,
        "data": {
            "company_name": str,
            "ticker": str, 
            "cik": str,
            "financials": {...},
            "match_score": int
        } or None,
        "error": str or None,
        "suggestions": [{"name": str, "score": int}] or []
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'company_name' not in data:
            return ErrorHandler.validation_error("Company name is required")
        
        company_name = data['company_name'].strip()
        if not company_name:
            return ErrorHandler.validation_error("Company name cannot be empty")
        
        threshold = data.get('threshold', 75)
        
        # Perform lookup
        result = sec_lookup_service.lookup_company(company_name, threshold)
        
        # Return the result directly since it already has the proper success/error structure
        return result
        
    except Exception as e:
        return ErrorHandler.processing_error(f"SEC lookup failed: {str(e)}")

@sec_lookup_bp.route('/select-company', methods=['POST'])  
def select_company():
    """
    Select a specific company from suggestions
    
    Request body:
    {
        "company_name": str (exact name from suggestions)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'company_name' not in data:
            return ErrorHandler.validation_error("Company name is required")
        
        company_name = data['company_name'].strip()
        if not company_name:
            return ErrorHandler.validation_error("Company name cannot be empty")
        
        # Force exact match with high threshold
        result = sec_lookup_service.lookup_company(company_name, threshold=95)
        
        # Return the result directly since it already has the proper success/error structure
        return result
        
    except Exception as e:
        return ErrorHandler.processing_error(f"Company selection failed: {str(e)}")
