from flask import Blueprint, request
import json
from services.file_service import FileService
from services.text_extractor import TextExtractor
from services.gemini_service import GeminiFinancialExtractor
from services.openrouter_service import OpenRouterService
from services.response_formatter import ResponseFormatter
from services.error_handler import ErrorHandler, handle_exceptions

investment_bp = Blueprint("investment", __name__)

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
    uploaded_files = request.files.getlist("files")

    if not uploaded_files or len(uploaded_files) == 0:
        return ErrorHandler.validation_error("No files uploaded")

    processed_files = []
    combined_text = ""
    total_length = 0

    try:
        for file in uploaded_files:
            if file.filename == "":
                continue

            filepath, filename = FileService.save_uploaded_file(file)
            extracted_text = TextExtractor.extract_text_from_file(filepath)

            processed_files.append(
                {
                    "filename": filename,
                    "filepath": filepath,
                    "text_length": len(extracted_text),
                    "text": extracted_text,
                }
            )

            if combined_text:
                combined_text += f"\n\n--- INVESTMENT FILE: {filename} ---\n\n"
            else:
                combined_text += f"--- INVESTMENT FILE: {filename} ---\n\n"

            combined_text += extracted_text
            total_length += len(extracted_text)

        if not processed_files:
            return ErrorHandler.validation_error("No valid files to process")

        if gemini_extractor:
            investment_analysis = gemini_extractor.analyze_investment_data(
                combined_text
            )
        else:
            investment_analysis = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
            }

        filenames = [f["filename"] for f in processed_files]

        return ResponseFormatter.format_investment_response(
            filename=f"{len(filenames)} files: " + ", ".join(filenames),
            text_length=total_length,
            investment_analysis=investment_analysis,
            file_count=len(processed_files),
            processed_files=filenames,
        )

    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass


@investment_bp.route("/investment-analyze-text", methods=["POST"])
@handle_exceptions
def analyze_investment_text():
    data = request.get_json()

    if not data or "text" not in data:
        return ErrorHandler.validation_error("No text provided")

    text = data["text"].strip()

    if not text:
        return ErrorHandler.validation_error("Empty text provided")

    try:
        if gemini_extractor:
            investment_analysis = gemini_extractor.analyze_investment_data(text)
        else:
            investment_analysis = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
            }

        return ResponseFormatter.format_investment_response(
            filename="Manual Text Input",
            text_length=len(text),
            investment_analysis=investment_analysis,
            file_count=0,
            processed_files=[],
        )

    except Exception as e:
        return ErrorHandler.processing_error(str(e))


@investment_bp.route("/investment-check-sufficiency", methods=["POST"])
@handle_exceptions
def check_investment_sufficiency():
    combined_text = ""
    processed_files = []

    try:
        content_type = request.content_type or ""
        is_multipart = content_type.startswith("multipart/form-data")
        is_json = content_type.startswith("application/json")

        valuation_data = None
        financial_data = None
        manual_text = ""

        if is_multipart or (request.files and "files" in request.files):
            if request.files and "files" in request.files:
                uploaded_files = request.files.getlist("files")

                for file in uploaded_files:
                    if file.filename == "":
                        continue

                    filepath, filename = FileService.save_uploaded_file(file)
                    extracted_text = TextExtractor.extract_text_from_file(filepath)

                    processed_files.append(
                        {
                            "filename": filename,
                            "filepath": filepath,
                            "text_length": len(extracted_text),
                        }
                    )

                    if combined_text:
                        combined_text += f"\n\n--- NEW FILE: {filename} ---\n\n"
                    else:
                        combined_text += f"--- NEW FILE: {filename} ---\n\n"

                    combined_text += extracted_text

            manual_text = request.form.get("manual_text", "").strip()

            try:
                valuation_data_str = request.form.get("valuation_data")
                if valuation_data_str:
                    valuation_data = json.loads(valuation_data_str)
            except json.JSONDecodeError:
                pass

            try:
                financial_data_str = request.form.get("financial_data")
                if financial_data_str:
                    financial_data = json.loads(financial_data_str)
            except json.JSONDecodeError:
                pass

        elif is_json:
            try:
                data = request.get_json()
                if data:
                    manual_text = data.get("manual_text", "").strip()
                    valuation_data = data.get("valuation_data")
                    financial_data = data.get("financial_data")
            except Exception as e:
                return ErrorHandler.validation_error(f"Invalid JSON data: {str(e)}")

        else:
            try:
                manual_text = request.form.get("manual_text", "").strip()
            except Exception:
                return ErrorHandler.validation_error(
                    "Unsupported content type. Please use multipart/form-data for file uploads or application/json for data."
                )

        analysis_sections = []

        if financial_data:
            analysis_sections.append("--- PREVIOUS FINANCIAL ANALYSIS ---")
            analysis_sections.append(
                json.dumps(financial_data, indent=2, ensure_ascii=False)
            )

        if valuation_data:
            analysis_sections.append("--- PREVIOUS VALUATION ANALYSIS ---")
            analysis_sections.append(
                json.dumps(valuation_data, indent=2, ensure_ascii=False)
            )

        if combined_text:
            analysis_sections.append(combined_text)

        if manual_text:
            analysis_sections.append("--- ADDITIONAL MANUAL INPUT ---")
            analysis_sections.append(manual_text)

        final_combined_text = "\n\n".join(analysis_sections)

        if not final_combined_text:
            return ErrorHandler.validation_error(
                "No data provided - please include financial data, valuation data, files, or manual text"
            )

        if gemini_extractor:
            sufficiency_result = gemini_extractor.check_investment_sufficiency(
                final_combined_text
            )
        else:
            sufficiency_result = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
            }

        return ResponseFormatter.format_sufficiency_response(sufficiency_result)

    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass


@investment_bp.route("/investment-calculate-validity", methods=["POST"])
@handle_exceptions
def calculate_investment_validity():
    processed_files = []
    additional_file_text = ""

    try:
        content_type = request.content_type or ""
        is_multipart = content_type.startswith("multipart/form-data")
        is_json = content_type.startswith("application/json")

        financial_data = None
        valuation_data = None
        investment_data = None

        if is_multipart:

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
                        "text_length": len(extracted_text),
                    })

                    if additional_file_text:
                        additional_file_text += f"\n\n--- ADDITIONAL FILE: {filename} ---\n\n"
                    else:
                        additional_file_text += f"--- ADDITIONAL FILE: {filename} ---\n\n"

                    additional_file_text += extracted_text

            try:
                financial_data_str = request.form.get("financial_data")
                if financial_data_str:
                    financial_data = json.loads(financial_data_str)
            except json.JSONDecodeError:
                pass

            try:
                valuation_data_str = request.form.get("valuation_data")
                if valuation_data_str:
                    valuation_data = json.loads(valuation_data_str)
            except json.JSONDecodeError:
                pass

            try:
                investment_data_str = request.form.get("investment_data")
                if investment_data_str:
                    investment_data = json.loads(investment_data_str)
            except json.JSONDecodeError:
                pass


        elif is_json:
            data = request.get_json()
            if data:
                financial_data = data.get("financial_data")
                valuation_data = data.get("valuation_data")
                investment_data = data.get("investment_data")
        else:
            return ErrorHandler.validation_error("Unsupported content type. Use multipart/form-data or application/json.")

        if not all([financial_data, valuation_data, investment_data]):
            return ErrorHandler.validation_error(
                "Financial data, valuation data, and investment data are all required"
            )

        if additional_file_text:
            if not isinstance(investment_data, dict):
                investment_data = {}

            investment_data["additional_file_content"] = additional_file_text
            investment_data["additional_files_count"] = len(processed_files)

            print(f"DEBUG VALIDITY: Added {len(processed_files)} additional files")
            print(f"DEBUG VALIDITY: Additional content length: {len(additional_file_text):,} characters")

        if openrouter_service:
            validity_result = openrouter_service.calculate_investment_validity(
                financial_data, valuation_data, investment_data
            )
        else:
            validity_result = {
                "success": False,
                "error": "OpenRouter API not configured. Please set OPENROUTER_API_KEY environment variable.",
            }

        return ResponseFormatter.format_validity_response(validity_result)

    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass


@investment_bp.route("/investment-calculate-validity-fast", methods=["POST"])
@handle_exceptions
def calculate_investment_validity_fast():
    processed_files = []
    additional_file_text = ""

    try:
        content_type = request.content_type or ""
        is_multipart = content_type.startswith("multipart/form-data")
        is_json = content_type.startswith("application/json")

        financial_data = None
        valuation_data = None
        investment_data = None

        if is_multipart:

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
                        "text_length": len(extracted_text),
                    })

                    if additional_file_text:
                        additional_file_text += f"\n\n--- ADDITIONAL FILE: {filename} ---\n\n"
                    else:
                        additional_file_text += f"--- ADDITIONAL FILE: {filename} ---\n\n"

                    additional_file_text += extracted_text

            try:
                financial_data_str = request.form.get("financial_data")
                if financial_data_str:
                    financial_data = json.loads(financial_data_str)
            except json.JSONDecodeError:
                pass

            try:
                valuation_data_str = request.form.get("valuation_data")
                if valuation_data_str:
                    valuation_data = json.loads(valuation_data_str)
            except json.JSONDecodeError:
                pass

            try:
                investment_data_str = request.form.get("investment_data")
                if investment_data_str:
                    investment_data = json.loads(investment_data_str)
            except json.JSONDecodeError:
                pass


        elif is_json:
            data = request.get_json()
            if data:
                financial_data = data.get("financial_data")
                valuation_data = data.get("valuation_data")
                investment_data = data.get("investment_data")
        else:
            return ErrorHandler.validation_error("Unsupported content type. Use multipart/form-data or application/json.")

        if not all([financial_data, valuation_data, investment_data]):
            return ErrorHandler.validation_error(
                "Financial data, valuation data, and investment data are all required"
            )

        if additional_file_text:
            if not isinstance(investment_data, dict):
                investment_data = {}

            investment_data["additional_file_content"] = additional_file_text
            investment_data["additional_files_count"] = len(processed_files)

            print(f"DEBUG FAST VALIDITY: Added {len(processed_files)} additional files")
            print(f"DEBUG FAST VALIDITY: Additional content length: {len(additional_file_text):,} characters")

        if gemini_extractor:
            validity_result = gemini_extractor.calculate_investment_validity_fast(
                financial_data, valuation_data, investment_data
            )
        else:
            validity_result = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
            }

        return ResponseFormatter.format_validity_response(validity_result)

    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass


@investment_bp.route("/investment-find-investors", methods=["POST"])
@handle_exceptions
def find_investors():
    processed_files = []
    additional_file_text = ""

    try:
        content_type = request.content_type or ""
        is_multipart = content_type.startswith("multipart/form-data")
        is_json = content_type.startswith("application/json")

        financial_data = None
        valuation_data = None
        investment_data = None

        if is_multipart:

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
                        "text_length": len(extracted_text),
                    })

                    if additional_file_text:
                        additional_file_text += f"\n\n--- ADDITIONAL FILE: {filename} ---\n\n"
                    else:
                        additional_file_text += f"--- ADDITIONAL FILE: {filename} ---\n\n"

                    additional_file_text += extracted_text

            try:
                financial_data_str = request.form.get("financial_data")
                if financial_data_str:
                    financial_data = json.loads(financial_data_str)
            except json.JSONDecodeError:
                pass

            try:
                valuation_data_str = request.form.get("valuation_data")
                if valuation_data_str:
                    valuation_data = json.loads(valuation_data_str)
            except json.JSONDecodeError:
                pass

            try:
                investment_data_str = request.form.get("investment_data")
                if investment_data_str:
                    investment_data = json.loads(investment_data_str)
            except json.JSONDecodeError:
                pass

        elif is_json:
            data = request.get_json()
            if data:
                financial_data = data.get("financial_data")
                valuation_data = data.get("valuation_data")
                investment_data = data.get("investment_data")
        else:
            return ErrorHandler.validation_error("Unsupported content type. Use multipart/form-data or application/json.")

        if not all([financial_data, valuation_data, investment_data]):
            return ErrorHandler.validation_error(
                "Financial data, valuation data, and investment data are all required"
            )

        if additional_file_text:
            if not isinstance(investment_data, dict):
                investment_data = {}

            investment_data["additional_file_content"] = additional_file_text
            investment_data["additional_files_count"] = len(processed_files)

            print(f"DEBUG INVESTOR SEARCH: Added {len(processed_files)} additional files")
            print(f"DEBUG INVESTOR SEARCH: Additional content length: {len(additional_file_text):,} characters")

        if gemini_extractor:
            investor_result = gemini_extractor.find_investors(
                financial_data, valuation_data, investment_data
            )
        else:
            investor_result = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
            }

        return ResponseFormatter.format_investor_response(investor_result)

    except Exception as e:
        return ErrorHandler.processing_error(str(e))
    finally:
        for file_info in processed_files:
            try:
                FileService.cleanup_file(file_info["filepath"])
            except:
                pass
