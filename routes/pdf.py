from flask import Blueprint, send_from_directory
from services.error_handler import ErrorHandler, handle_exceptions
from config import Config

pdf_bp = Blueprint('pdf', __name__)

@pdf_bp.route("/pdfs/<filename>")
@handle_exceptions
def serve_pdf(filename):
    try:
        return send_from_directory(Config.PDF_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        return ErrorHandler.file_error("PDF file not found")
