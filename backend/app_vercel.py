import logging
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import uuid
import time
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

# Global progress tracking
upload_progress = {
    'status': 'idle',
    'message': '',
    'progress': 0,
    'stage': ''
}

# Add global error handler to ensure JSON responses
@app.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'The server encountered an unexpected error'
    }), 500

@app.errorhandler(404)
def not_found(error):
    logger.error(f"Not found error: {error}")
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist'
    }), 404

@app.errorhandler(400)
def bad_request(error):
    logger.error(f"Bad request error: {error}")
    return jsonify({
        'error': 'Bad request',
        'message': 'The request was invalid'
    }), 400

@app.route('/')
def index():
    return send_from_directory('../client', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('../client', filename)

@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    try:
        logger.info("🚀 Starting PDF upload process...")
        update_progress('uploading', 'Starting upload...', 10, 'upload')
        
        if 'file' not in request.files:
            logger.error("❌ No file provided in request")
            update_progress('error', 'No file provided', 0, 'upload')
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("❌ No file selected")
            update_progress('error', 'No file selected', 0, 'upload')
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            logger.error(f"❌ Invalid file type: {file.filename}")
            update_progress('error', 'Only PDF files are allowed', 0, 'upload')
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        logger.info(f"📄 Processing file: {file.filename} ({len(file.read())/1024:.1f} KB)")
        file.seek(0)  # Reset file pointer
        
        # Save uploaded file to backend
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logger.info(f"✅ File saved to: {file_path}")
        update_progress('processing', 'File uploaded successfully', 25, 'upload')
        
        # Simulate processing (since we don't have LangChain/Qdrant)
        update_progress('processing', 'Extracting text from PDF...', 40, 'processing')
        time.sleep(1)
        
        update_progress('processing', 'Creating vector embeddings...', 60, 'indexing')
        time.sleep(1)
        
        update_progress('processing', 'Indexing documents...', 80, 'indexing')
        time.sleep(1)
        
        update_progress('completed', 'Document indexed successfully!', 100, 'completed')
        
        # Clean up file
        os.remove(file_path)
        logger.info(f"🗑️  Cleaned up file: {file_path}")
        
        # Reset progress after successful completion
        update_progress('idle', '', 0, '')
        
        collection_name = f"rag_pdf_{uuid.uuid4().hex[:8]}"
        
        return jsonify({
            'message': 'Document indexed successfully (simulated mode)',
            'collection_name': collection_name,
            'chunks_count': 10,
            'note': 'This is running in simulated mode. Full RAG functionality requires LangChain, Qdrant, and Google Gemini.'
        })
            
    except Exception as e:
        logger.error(f"❌ Upload endpoint error: {str(e)}")
        update_progress('error', f'Upload error: {str(e)}', 0, 'upload')
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        logger.info("💬 Starting chat request...")
        
        # Check if request has JSON
        if not request.is_json:
            logger.error("❌ Request is not JSON")
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        if not data:
            logger.error("❌ No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
            
        user_query = data.get('query', '')
        collection_name = data.get('collection_name', 'chat_with_pdf')
        
        if not user_query:
            logger.error("❌ No query provided")
            return jsonify({'error': 'No query provided'}), 400
        
        logger.info(f"🤔 User query: {user_query}")
        logger.info(f"📚 Using collection: {collection_name}")
        
        # Simulate chat response
        return jsonify({
            'answer': f'This is a simulated response to: "{user_query}". Full chat functionality requires LangChain, Qdrant, and Google Gemini to be properly configured.',
            'sources': [
                {
                    'page': 1,
                    'content': 'This is a simulated source content from the document...',
                    'source': 'uploaded_document.pdf'
                }
            ]
        })
        
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {str(e)}")
        return jsonify({'error': f'Chat service error: {str(e)}'}), 500

@app.route('/api/progress', methods=['GET'])
def get_progress():
    try:
        # Ensure we return proper JSON response
        response_data = {
            'status': upload_progress.get('status', 'idle'),
            'message': upload_progress.get('message', ''),
            'progress': upload_progress.get('progress', 0),
            'stage': upload_progress.get('stage', '')
        }
        
        # Use jsonify for proper JSON response with correct headers
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Progress endpoint error: {str(e)}")
        # Return a safe fallback response with proper JSON
        error_response = {
            'status': 'error',
            'message': 'Progress tracking unavailable',
            'progress': 0,
            'stage': ''
        }
        return jsonify(error_response), 500

def update_progress(status, message, progress=0, stage=''):
    global upload_progress
    upload_progress = {
        'status': status,
        'message': message,
        'progress': progress,
        'stage': stage
    }
    logger.info(f"📊 Progress Update: {status} - {message} ({progress}%)")

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint to verify deployment"""
    return jsonify({
        'status': 'working',
        'message': 'Backend is deployed and working',
        'timestamp': str(time.time())
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        # Check if environment variables are set
        required_env_vars = ['GEMINI_API_KEY', 'QDRANT_URL', 'QDRANT_API_KEY']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            return jsonify({
                'status': 'warning',
                'message': f'Missing environment variables: {", ".join(missing_vars)} - running in simulated mode'
            })
        
        return jsonify({'status': 'healthy'})
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# For local testing
if __name__ == '__main__':
    app.run(debug=True, port=5010, host='0.0.0.0')
