from flask import Blueprint, request
from services.file_service import FileService
from services.text_extractor import TextExtractor
from services.gemini_service import GeminiFinancialExtractor
from services.response_formatter import ResponseFormatter
from services.error_handler import ErrorHandler, handle_exceptions

evaluation_bp = Blueprint("evaluation", __name__)

gemini_extractor = None
try:
    gemini_extractor = GeminiFinancialExtractor()
except ValueError as e:
    print(f"Warning: Gemini not initialized - {e}")


@evaluation_bp.route("/evaluate", methods=["POST"])
@handle_exceptions
def evaluate():
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
                combined_text += f"\n\n--- FILE: {filename} ---\n\n"
            else:
                combined_text += f"--- FILE: {filename} ---\n\n"

            combined_text += extracted_text
            total_length += len(extracted_text)

        if not processed_files:
            return ErrorHandler.validation_error("No valid files to process")

        if gemini_extractor:
            financial_analysis = gemini_extractor.extract_financial_data(combined_text)
        else:
            financial_analysis = {
                "success": False,
                "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
            }
        filenames = [f["filename"] for f in processed_files]

        return ResponseFormatter.format_evaluation_response(
            filename=f"{len(filenames)} files: " + ", ".join(filenames),
            text_length=total_length,
            financial_analysis=financial_analysis,
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
