from flask import Flask, request, jsonify
import os
from extractor import extract_text_from_file   # <-- we use your extractor

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

        # For debugging – return a preview (first 500 chars only)
        preview = extracted_text[:500] if extracted_text else ""

        return jsonify({
            "message": "success",
            "filename": file.filename,
            "preview": preview,
            "length": len(extracted_text)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
