from flask import jsonify
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class ErrorHandler:
    @staticmethod
    def create_error_response(message, status_code=500, error_type="server_error"):
        return jsonify({
            "error": message,
            "error_type": error_type,
            "success": False
        }), status_code
    
    @staticmethod
    def validation_error(message):
        return ErrorHandler.create_error_response(message, 400, "validation_error")
    
    @staticmethod
    def file_error(message):
        return ErrorHandler.create_error_response(message, 400, "file_error")
    
    @staticmethod
    def processing_error(message):
        return ErrorHandler.create_error_response(message, 500, "processing_error")
    
    @staticmethod
    def api_error(message):
        return ErrorHandler.create_error_response(message, 503, "api_error")

def handle_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
            return ErrorHandler.file_error(f"File not found: {str(e)}")
        except PermissionError as e:
            logger.error(f"Permission denied: {str(e)}")
            return ErrorHandler.file_error(f"Permission denied: {str(e)}")
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return ErrorHandler.validation_error(str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return ErrorHandler.processing_error(f"An unexpected error occurred: {str(e)}")
    
    return decorated_function
