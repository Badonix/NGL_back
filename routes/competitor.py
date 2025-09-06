from flask import Blueprint, request
import json
from services.file_service import FileService
from services.text_extractor import TextExtractor
from services.gemini_service import GeminiFinancialExtractor
from services.response_formatter import ResponseFormatter
from services.error_handler import ErrorHandler, handle_exceptions

competitor_bp = Blueprint("competitor", __name__)

# Initialize Gemini service
gemini_extractor = GeminiFinancialExtractor()

@competitor_bp.route("/competitor-analyze", methods=["POST"])
@handle_exceptions
def analyze_competitors():
    """
    Analyze uploaded company documents to identify competitors in the same industry
    """
    processed_files = []
    try:
        # Check if files are uploaded
        if "files" not in request.files:
            return ErrorHandler.validation_error("No files uploaded")

        uploaded_files = request.files.getlist("files")
        if not uploaded_files or all(file.filename == "" for file in uploaded_files):
            return ErrorHandler.validation_error("No files selected")

        # Process uploaded files
        combined_text = ""
        for file in uploaded_files:
            if file.filename == "":
                continue

            # Save file temporarily
            filepath, filename = FileService.save_uploaded_file(file)
            processed_files.append({
                "filename": filename,
                "filepath": filepath
            })

            # Extract text from file
            extracted_text = TextExtractor.extract_text_from_file(filepath)
            
            if combined_text:
                combined_text += f"\n\n--- FILE: {filename} ---\n\n"
            else:
                combined_text += f"--- FILE: {filename} ---\n\n"
            combined_text += extracted_text

        if not combined_text.strip():
            return ErrorHandler.validation_error("No readable content found in uploaded files")

        # Analyze competitors using Gemini
        if gemini_extractor:
            competitor_result = gemini_extractor.analyze_competitors(combined_text)
        else:
            competitor_result = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
            }

        return ResponseFormatter.format_competitor_response(competitor_result)

    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        # Clean up uploaded files
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass


@competitor_bp.route("/competitor-compare", methods=["POST"])
@handle_exceptions
def compare_companies():
    """
    Compare two companies based on their uploaded documents
    """
    processed_files = []
    try:
        # Check if files are uploaded
        if "company_a_files" not in request.files or "company_b_files" not in request.files:
            return ErrorHandler.validation_error("Both company A and company B files are required")

        company_a_files = request.files.getlist("company_a_files")
        company_b_files = request.files.getlist("company_b_files")
        
        if not company_a_files or not company_b_files:
            return ErrorHandler.validation_error("Both companies must have files uploaded")
        
        if all(file.filename == "" for file in company_a_files) or all(file.filename == "" for file in company_b_files):
            return ErrorHandler.validation_error("Both companies must have valid files")

        # Process Company A files
        company_a_text = ""
        for file in company_a_files:
            if file.filename == "":
                continue

            filepath, filename = FileService.save_uploaded_file(file)
            processed_files.append({
                "filename": filename,
                "filepath": filepath
            })

            extracted_text = TextExtractor.extract_text_from_file(filepath)
            
            if company_a_text:
                company_a_text += f"\n\n--- FILE: {filename} ---\n\n"
            else:
                company_a_text += f"--- FILE: {filename} ---\n\n"
            company_a_text += extracted_text

        # Process Company B files
        company_b_text = ""
        for file in company_b_files:
            if file.filename == "":
                continue

            filepath, filename = FileService.save_uploaded_file(file)
            processed_files.append({
                "filename": filename,
                "filepath": filepath
            })

            extracted_text = TextExtractor.extract_text_from_file(filepath)
            
            if company_b_text:
                company_b_text += f"\n\n--- FILE: {filename} ---\n\n"
            else:
                company_b_text += f"--- FILE: {filename} ---\n\n"
            company_b_text += extracted_text

        if not company_a_text.strip() or not company_b_text.strip():
            return ErrorHandler.validation_error("No readable content found in one or both companies' files")

        # Compare companies using Gemini
        if gemini_extractor:
            comparison_result = gemini_extractor.compare_companies(company_a_text, company_b_text)
        else:
            comparison_result = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
            }

        return ResponseFormatter.format_comparison_response(comparison_result)

    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        # Clean up uploaded files
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass
