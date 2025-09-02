from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from extractor import extract_text_from_file
from gemini_service import GeminiFinancialExtractor

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
PUBLIC_FOLDER = "public"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PUBLIC_FOLDER, exist_ok=True)
os.makedirs(f"{PUBLIC_FOLDER}/pdfs", exist_ok=True)

gemini_extractor = None
try:
    gemini_extractor = GeminiFinancialExtractor()
except ValueError as e:
    print(f"Warning: Gemini not initialized - {e}")


@app.route("/evaluate", methods=["POST"])
def evaluate():
    if "files" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["files"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        extracted_text = extract_text_from_file(filepath)

        preview = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text

        response_data = {
            "message": "success",
            "filename": file.filename,
            "length": len(extracted_text),
        }

        if gemini_extractor:
            financial_analysis = gemini_extractor.extract_financial_data(extracted_text)
            response_data["success"] = True
            response_data["data"] = {
                "financial_analysis": financial_analysis
            }
            
            # Include PDF information if available
            if financial_analysis.get("success") and financial_analysis.get("pdf_result"):
                pdf_result = financial_analysis["pdf_result"]
                if pdf_result.get("success"):
                    response_data["pdf"] = {
                        "available": True,
                        "filename": os.path.basename(pdf_result["file_path"]),
                        "url": pdf_result.get("public_url", f"/pdfs/{os.path.basename(pdf_result['file_path'])}")
                    }
                else:
                    response_data["pdf"] = {
                        "available": False,
                        "error": pdf_result.get("error", "PDF generation failed")
                    }
            else:
                response_data["pdf"] = {
                    "available": False,
                    "error": "No summarized data available for PDF generation"
                }
        else:
            response_data["success"] = False
            response_data["data"] = {
                "financial_analysis": {
                    "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
                }
            }
            response_data["pdf"] = {
                "available": False,
                "error": "Gemini API not configured"
            }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/pdfs/<filename>")
def serve_pdf(filename):
    """Serve PDF files from the public/pdfs directory"""
    try:
        return send_from_directory(f"{PUBLIC_FOLDER}/pdfs", filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "PDF file not found"}), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
