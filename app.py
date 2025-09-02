from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from extractor import extract_text_from_file
from gemini_service import GeminiFinancialExtractor

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        else:
            response_data["success"] = False
            response_data["data"] = {
                "financial_analysis": {
                    "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
                }
            }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
