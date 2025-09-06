from flask import Blueprint, request
import json
from services.file_service import FileService
from services.text_extractor import TextExtractor
from services.gemini_service import GeminiFinancialExtractor
from services.response_formatter import ResponseFormatter
from services.error_handler import ErrorHandler, handle_exceptions

competitor_bp = Blueprint("competitor", __name__)

gemini_extractor = GeminiFinancialExtractor()

@competitor_bp.route("/competitor-analyze", methods=["POST"])
@handle_exceptions
def analyze_competitors():
    """
    Analyze company documents and/or SEC data to identify competitors in the same industry
    """
    processed_files = []
    try:
        uploaded_files = request.files.getlist("files") if "files" in request.files else []

        company_sec_data = None
        if "company_sec_data" in request.form:
            try:
                company_sec_data = json.loads(request.form["company_sec_data"])
            except json.JSONDecodeError:
                return ErrorHandler.validation_error("Invalid SEC data format")

        has_files = uploaded_files and not all(file.filename == "" for file in uploaded_files)
        if not has_files and not company_sec_data:
            return ErrorHandler.validation_error("Either files or company SEC data must be provided")

        combined_text = ""

        if company_sec_data:
            combined_text += "--- SEC FINANCIAL DATA ---\n\n"
            combined_text += f"Company: {company_sec_data.get('company_name', 'Unknown')}\n"
            if company_sec_data.get('ticker'):
                combined_text += f"Ticker: {company_sec_data['ticker']}\n"
            combined_text += f"CIK: {company_sec_data.get('cik', 'Unknown')}\n\n"

            financials = company_sec_data.get('financials', {})
            combined_text += "FINANCIAL METRICS:\n"
            if financials.get('revenue'):
                combined_text += f"Revenue: ${financials['revenue']:,.2f}\n"
            if financials.get('net_income'):
                combined_text += f"Net Income: ${financials['net_income']:,.2f}\n"
            if financials.get('total_assets'):
                combined_text += f"Total Assets: ${financials['total_assets']:,.2f}\n"
            if financials.get('total_liabilities'):
                combined_text += f"Total Liabilities: ${financials['total_liabilities']:,.2f}\n"
            if financials.get('cash_and_equivalents'):
                combined_text += f"Cash & Equivalents: ${financials['cash_and_equivalents']:,.2f}\n"
            combined_text += "\n"

        for file in uploaded_files:
            if file.filename == "":
                continue

            filepath, filename = FileService.save_uploaded_file(file)
            processed_files.append({
                "filename": filename,
                "filepath": filepath
            })

            extracted_text = TextExtractor.extract_text_from_file(filepath)

            if combined_text:
                combined_text += f"\n\n--- FILE: {filename} ---\n\n"
            else:
                combined_text += f"--- FILE: {filename} ---\n\n"
            combined_text += extracted_text

        if not combined_text.strip():
            return ErrorHandler.validation_error("No readable content found for analysis")

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
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass


@competitor_bp.route("/competitor-compare", methods=["POST"])
@handle_exceptions
def compare_companies():
    """
    Compare two companies based on their uploaded documents and/or SEC data
    """
    processed_files = []
    try:
        company_a_files = request.files.getlist("company_a_files") if "company_a_files" in request.files else []
        company_b_files = request.files.getlist("company_b_files") if "company_b_files" in request.files else []

        company_a_sec_data = None
        company_b_sec_data = None

        if "company_a_sec_data" in request.form:
            try:
                company_a_sec_data = json.loads(request.form["company_a_sec_data"])
            except json.JSONDecodeError:
                return ErrorHandler.validation_error("Invalid SEC data format for company A")

        if "company_b_sec_data" in request.form:
            try:
                company_b_sec_data = json.loads(request.form["company_b_sec_data"])
            except json.JSONDecodeError:
                return ErrorHandler.validation_error("Invalid SEC data format for company B")

        has_company_a_data = (company_a_files and not all(file.filename == "" for file in company_a_files)) or company_a_sec_data
        has_company_b_data = (company_b_files and not all(file.filename == "" for file in company_b_files)) or company_b_sec_data

        if not has_company_a_data or not has_company_b_data:
            return ErrorHandler.validation_error("Both companies must have either uploaded files or SEC data")

        company_a_text = ""

        if company_a_sec_data:
            company_a_text += "--- SEC FINANCIAL DATA ---\n\n"
            company_a_text += f"Company: {company_a_sec_data.get('company_name', 'Unknown')}\n"
            if company_a_sec_data.get('ticker'):
                company_a_text += f"Ticker: {company_a_sec_data['ticker']}\n"
            company_a_text += f"CIK: {company_a_sec_data.get('cik', 'Unknown')}\n\n"

            financials = company_a_sec_data.get('financials', {})
            company_a_text += "FINANCIAL METRICS:\n"
            if financials.get('revenue'):
                company_a_text += f"Revenue: ${financials['revenue']:,.2f}\n"
            if financials.get('net_income'):
                company_a_text += f"Net Income: ${financials['net_income']:,.2f}\n"
            if financials.get('total_assets'):
                company_a_text += f"Total Assets: ${financials['total_assets']:,.2f}\n"
            if financials.get('total_liabilities'):
                company_a_text += f"Total Liabilities: ${financials['total_liabilities']:,.2f}\n"
            if financials.get('cash_and_equivalents'):
                company_a_text += f"Cash & Equivalents: ${financials['cash_and_equivalents']:,.2f}\n"
            company_a_text += "\n"

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

        company_b_text = ""

        if company_b_sec_data:
            company_b_text += "--- SEC FINANCIAL DATA ---\n\n"
            company_b_text += f"Company: {company_b_sec_data.get('company_name', 'Unknown')}\n"
            if company_b_sec_data.get('ticker'):
                company_b_text += f"Ticker: {company_b_sec_data['ticker']}\n"
            company_b_text += f"CIK: {company_b_sec_data.get('cik', 'Unknown')}\n\n"

            financials = company_b_sec_data.get('financials', {})
            company_b_text += "FINANCIAL METRICS:\n"
            if financials.get('revenue'):
                company_b_text += f"Revenue: ${financials['revenue']:,.2f}\n"
            if financials.get('net_income'):
                company_b_text += f"Net Income: ${financials['net_income']:,.2f}\n"
            if financials.get('total_assets'):
                company_b_text += f"Total Assets: ${financials['total_assets']:,.2f}\n"
            if financials.get('total_liabilities'):
                company_b_text += f"Total Liabilities: ${financials['total_liabilities']:,.2f}\n"
            if financials.get('cash_and_equivalents'):
                company_b_text += f"Cash & Equivalents: ${financials['cash_and_equivalents']:,.2f}\n"
            company_b_text += "\n"

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
            return ErrorHandler.validation_error("No readable content found for one or both companies")

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
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass
