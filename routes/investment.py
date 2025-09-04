from flask import Blueprint, request
import json
from services.file_service import FileService
from services.text_extractor import TextExtractor
from services.gemini_service import GeminiFinancialExtractor
from services.openrouter_service import OpenRouterService
from services.response_formatter import ResponseFormatter
from services.error_handler import ErrorHandler, handle_exceptions

investment_bp = Blueprint('investment', __name__)

gemini_extractor = None
try:
    gemini_extractor = GeminiFinancialExtractor()
except ValueError as e:
    print(f"Warning: Gemini not initialized - {e}")

openrouter_service = None
try:
    openrouter_service = OpenRouterService()
except ValueError as e:
    print(f"Warning: OpenRouter not initialized - {e}")

@investment_bp.route("/investment-analyze", methods=["POST"])
@handle_exceptions
def analyze_investment_files():
    if "files" not in request.files:
        return ErrorHandler.validation_error("No files uploaded")
    
    # Get all files with the same field name
    uploaded_files = request.files.getlist("files")
    
    if not uploaded_files or len(uploaded_files) == 0:
        return ErrorHandler.validation_error("No files uploaded")
    
    processed_files = []
    combined_text = ""
    total_length = 0
    
    try:
        # Process each file
        for file in uploaded_files:
            if file.filename == "":
                continue  # Skip empty files
                
            filepath, filename = FileService.save_uploaded_file(file)
            extracted_text = TextExtractor.extract_text_from_file(filepath)
            
            processed_files.append({
                "filename": filename,
                "filepath": filepath,
                "text_length": len(extracted_text),
                "text": extracted_text
            })
            
            # Combine text with file separators
            if combined_text:
                combined_text += f"\n\n--- INVESTMENT FILE: {filename} ---\n\n"
            else:
                combined_text += f"--- INVESTMENT FILE: {filename} ---\n\n"
            
            combined_text += extracted_text
            total_length += len(extracted_text)
        
        if not processed_files:
            return ErrorHandler.validation_error("No valid files to process")
        
        # Process combined text with Gemini for investment analysis
        if gemini_extractor:
            investment_analysis = gemini_extractor.analyze_investment_data(combined_text)
        else:
            investment_analysis = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
            }
        
        # Create file list for response
        filenames = [f["filename"] for f in processed_files]
        
        return ResponseFormatter.format_investment_response(
            filename=f"{len(filenames)} files: " + ", ".join(filenames),
            text_length=total_length,
            investment_analysis=investment_analysis,
            file_count=len(processed_files),
            processed_files=filenames
        )
        
    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        # Cleanup all processed files
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass

@investment_bp.route("/investment-analyze-text", methods=["POST"])
@handle_exceptions
def analyze_investment_text():
    data = request.get_json()
    
    if not data or 'text' not in data:
        return ErrorHandler.validation_error("No text provided")
    
    text = data['text'].strip()
    
    if not text:
        return ErrorHandler.validation_error("Empty text provided")
    
    try:
        # Process text with Gemini for investment analysis
        if gemini_extractor:
            investment_analysis = gemini_extractor.analyze_investment_data(text)
        else:
            investment_analysis = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
            }
        
        return ResponseFormatter.format_investment_response(
            filename="Manual Text Input",
            text_length=len(text),
            investment_analysis=investment_analysis,
            file_count=0,
            processed_files=[]
        )
        
    except Exception as e:
        return ErrorHandler.processing_error(str(e))

@investment_bp.route("/investment-check-sufficiency", methods=["POST"])
@handle_exceptions
def check_investment_sufficiency():
    # Handle comprehensive investment data including previous analysis
    combined_text = ""
    processed_files = []
    
    try:
        # Determine the content type and handle accordingly
        content_type = request.content_type or ""
        is_multipart = content_type.startswith('multipart/form-data')
        is_json = content_type.startswith('application/json')
        
        # Initialize data containers
        valuation_data = None
        financial_data = None
        manual_text = ""
        
        # Handle multipart form data (file uploads + JSON data)
        if is_multipart or (request.files and "files" in request.files):
            # Process uploaded files
            if request.files and "files" in request.files:
                uploaded_files = request.files.getlist("files")
                
                for file in uploaded_files:
                    if file.filename == "":
                        continue
                        
                    filepath, filename = FileService.save_uploaded_file(file)
                    extracted_text = TextExtractor.extract_text_from_file(filepath)
                    
                    processed_files.append({
                        "filename": filename,
                        "filepath": filepath,
                        "text_length": len(extracted_text)
                    })
                    
                    # Combine text with file separators
                    if combined_text:
                        combined_text += f"\n\n--- NEW FILE: {filename} ---\n\n"
                    else:
                        combined_text += f"--- NEW FILE: {filename} ---\n\n"
                    
                    combined_text += extracted_text
            
            # Get data from form fields
            manual_text = request.form.get('manual_text', '').strip()
            
            # Try to get JSON data from form fields
            try:
                valuation_data_str = request.form.get('valuation_data')
                if valuation_data_str:
                    valuation_data = json.loads(valuation_data_str)
            except json.JSONDecodeError:
                pass
                
            try:
                financial_data_str = request.form.get('financial_data')
                if financial_data_str:
                    financial_data = json.loads(financial_data_str)
            except json.JSONDecodeError:
                pass
            
        elif is_json:
            # Handle JSON request with all data types
            try:
                data = request.get_json()
                if data:
                    manual_text = data.get('manual_text', '').strip()
                    valuation_data = data.get('valuation_data')
                    financial_data = data.get('financial_data')
            except Exception as e:
                return ErrorHandler.validation_error(f"Invalid JSON data: {str(e)}")
        
        else:
            # Try to handle as form data fallback
            try:
                manual_text = request.form.get('manual_text', '').strip()
            except Exception:
                return ErrorHandler.validation_error("Unsupported content type. Please use multipart/form-data for file uploads or application/json for data.")
        
        # Build comprehensive analysis text
        analysis_sections = []
        
        # Add previous financial analysis data
        if financial_data:
            analysis_sections.append("--- PREVIOUS FINANCIAL ANALYSIS ---")
            analysis_sections.append(json.dumps(financial_data, indent=2, ensure_ascii=False))
        
        # Add previous valuation data
        if valuation_data:
            analysis_sections.append("--- PREVIOUS VALUATION ANALYSIS ---")
            analysis_sections.append(json.dumps(valuation_data, indent=2, ensure_ascii=False))
        
        # Add new file content
        if combined_text:
            analysis_sections.append(combined_text)
        
        # Add manual input
        if manual_text:
            analysis_sections.append("--- ADDITIONAL MANUAL INPUT ---")
            analysis_sections.append(manual_text)
        
        # Combine all sections
        final_combined_text = "\n\n".join(analysis_sections)
        
        if not final_combined_text:
            return ErrorHandler.validation_error("No data provided - please include financial data, valuation data, files, or manual text")
        
        # Use Gemini service to check sufficiency
        if gemini_extractor:
            sufficiency_result = gemini_extractor.check_investment_sufficiency(final_combined_text)
        else:
            sufficiency_result = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
            }
        
        return ResponseFormatter.format_sufficiency_response(sufficiency_result)
        
    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        # Cleanup uploaded files
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass

@investment_bp.route("/investment-calculate-validity", methods=["POST"])
@handle_exceptions 
def calculate_investment_validity():
    data = request.get_json()
    
    if not data:
        return ErrorHandler.validation_error("No data provided")
    
    # Extract the required data sources
    financial_data = data.get('financial_data')
    valuation_data = data.get('valuation_data') 
    investment_data = data.get('investment_data')
    
    if not all([financial_data, valuation_data, investment_data]):
        return ErrorHandler.validation_error("Financial data, valuation data, and investment data are all required")
    
    try:
        if openrouter_service:
            validity_result = openrouter_service.calculate_investment_validity(
                financial_data, valuation_data, investment_data
            )
        else:
            validity_result = {
                "success": False,
                "error": "OpenRouter API not configured. Please set OPENROUTER_API_KEY environment variable."
            }
        
        return ResponseFormatter.format_validity_response(validity_result)
        
    except Exception as e:
        return ErrorHandler.processing_error(str(e))
