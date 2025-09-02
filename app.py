from flask import Flask, request, jsonify
import os
import random
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'docx', 'doc'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/evaluate', methods=['POST'])
def evaluate_financial_project():
    """
    Endpoint to receive files for financial evaluation
    Accepts: PDF, Excel (.xlsx, .xls), Word (.docx, .doc) files
    Returns: Random evaluation response for testing
    """
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No files selected'}), 400
    
    uploaded_files = []
    errors = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            uploaded_files.append({
                'filename': filename,
                'size': os.path.getsize(file_path),
                'type': filename.rsplit('.', 1)[1].lower()
            })
        else:
            errors.append(f"File {file.filename} has invalid extension")
    
    if errors:
        return jsonify({'error': 'Invalid files', 'details': errors}), 400
    
    # Generate random response for testing
    random_responses = [
        {
            'status': 'approved',
            'confidence': random.uniform(0.7, 0.95),
            'risk_level': 'low',
            'recommendation': 'Proceed with investment',
            'estimated_return': f"{random.uniform(5, 15):.1f}%"
        },
        {
            'status': 'conditional',
            'confidence': random.uniform(0.5, 0.7),
            'risk_level': 'medium',
            'recommendation': 'Proceed with additional due diligence',
            'estimated_return': f"{random.uniform(3, 8):.1f}%"
        },
        {
            'status': 'rejected',
            'confidence': random.uniform(0.6, 0.9),
            'risk_level': 'high',
            'recommendation': 'Do not proceed with investment',
            'estimated_return': f"{random.uniform(-5, 2):.1f}%"
        }
    ]
    
    response = random.choice(random_responses)
    response['files_processed'] = len(uploaded_files)
    response['uploaded_files'] = uploaded_files
    
    return jsonify(response), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Financial evaluation API is running'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
