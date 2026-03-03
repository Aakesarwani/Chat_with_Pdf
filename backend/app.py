import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import tempfile
import uuid
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
import google.generativeai as genai
import time
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

def get_qdrant_client():
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

def get_vector_store(collection_name="chat_with_pdf"):
    embeddings = get_embeddings()
    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name=collection_name,
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )

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
        
        # Generate unique collection name
        collection_name = f"rag_pdf_{uuid.uuid4().hex[:8]}"
        logger.info(f"🆔 Generated collection name: {collection_name}")
        
        def index_document():
            try:
                update_progress('processing', 'Starting document indexing...', 30, 'indexing')
                
                # Load PDF from local file
                logger.info(f"📖 Loading PDF from: {file_path}")
                update_progress('processing', 'Loading PDF...', 40, 'indexing')
                loader = PyPDFLoader(file_path=file_path)
                docs = loader.load()
                logger.info(f"✅ Successfully loaded {len(docs)} pages from PDF")
                update_progress('processing', f'Loaded {len(docs)} pages', 50, 'indexing')
                
                # Chunk documents
                logger.info("✂️  Chunking documents...")
                update_progress('processing', 'Chunking documents...', 60, 'indexing')
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                chunks = text_splitter.split_documents(docs)
                logger.info(f"🧩 Created {len(chunks)} chunks")
                update_progress('processing', f'Created {len(chunks)} chunks', 70, 'indexing')
                
                # Get embeddings and client
                logger.info("🔗 Setting up embeddings and Qdrant client...")
                update_progress('processing', 'Setting up vector database...', 80, 'indexing')
                embeddings = get_embeddings()
                qdrant_client = get_qdrant_client()
                
                # Check if collection exists and delete it (for cleanup)
                try:
                    qdrant_client.get_collection(collection_name)
                    qdrant_client.delete_collection(collection_name)
                    logger.info(f"🗑️  Deleted existing collection: {collection_name}")
                except:
                    logger.info("ℹ️  Collection doesn't exist yet (this is normal)")
                    pass  # Collection doesn't exist, which is fine
                
                # Create new collection
                logger.info("🏗️  Creating new Qdrant collection...")
                update_progress('processing', 'Creating vector collection...', 85, 'indexing')
                qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=3072, distance=Distance.COSINE)
                )
                logger.info(f"✅ Created new collection: {collection_name}")
                
                # Create vector store and add documents
                logger.info("🧠 Setting up vector store...")
                vector_store = Qdrant(
                    client=qdrant_client,
                    collection_name=collection_name,
                    embeddings=embeddings
                )
                
                # Add documents in batches
                batch_size = 5
                total_chunks = len(chunks)
                logger.info(f"📦 Adding {total_chunks} chunks in batches of {batch_size}...")
                
                for i in range(0, total_chunks, batch_size):
                    batch = chunks[i:i + batch_size]
                    batch_num = i//batch_size + 1
                    total_batches = (total_chunks + batch_size - 1)//batch_size
                    progress_percent = 85 + (15 * (batch_num / total_batches))
                    
                    logger.info(f"📤 Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")
                    update_progress('processing', f'Processing batch {batch_num}/{total_batches}', int(progress_percent), 'indexing')
                    vector_store.add_documents(batch)
                    
                    if i + batch_size < total_chunks:
                        logger.info("⏳ Waiting 2 seconds to avoid rate limiting...")
                        time.sleep(2)  # Rate limiting
                
                # Delete the uploaded file after successful indexing
                os.remove(file_path)
                logger.info(f"🗑️  Deleted uploaded file: {file_path}")
                
                logger.info("🎉 Indexing completed successfully!")
                update_progress('completed', 'Document indexed successfully!', 100, 'completed')
                return True, collection_name, len(chunks)
                
            except Exception as e:
                logger.error(f"❌ Indexing failed: {str(e)}")
                update_progress('error', f'Indexing failed: {str(e)}', 0, 'indexing')
                # Clean up file on error
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"🧹 Cleaned up file after error: {file_path}")
                return False, str(e), 0
        
        # Run indexing
        logger.info("🚀 Starting indexing process...")
        success, result, chunks_count = index_document()
        
        if success:
            logger.info(f"🎉 Upload and indexing completed! Collection: {collection_name}, Chunks: {chunks_count}")
            # Reset progress after successful completion
            update_progress('idle', '', 0, '')
            return jsonify({
                'message': 'Document indexed successfully',
                'collection_name': collection_name,
                'chunks_count': chunks_count,
                'note': 'Document is ready for questions. Note: Due to API limits, responses may be limited.'
            })
        else:
            logger.error(f"❌ Upload failed: {result}")
            # Check if it's a quota error and provide a helpful message
            if 'RESOURCE_EXHAUSTED' in result or 'quota' in result.lower():
                return jsonify({
                    'error': 'API quota exceeded. The free tier limit has been reached. Please try again later or upgrade your API plan.',
                    'details': result,
                    'quota_error': True
                }), 429
            else:
                return jsonify({'error': f'Indexing failed: {result}'}), 500
            
    except Exception as e:
        logger.error(f"❌ Upload endpoint error: {str(e)}")
        update_progress('error', f'Upload error: {str(e)}', 0, 'upload')
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        logger.info("💬 Starting chat request...")
        
        data = request.get_json()
        user_query = data.get('query', '')
        collection_name = data.get('collection_name', 'chat_with_pdf')
        
        if not user_query:
            logger.error("❌ No query provided")
            return jsonify({'error': 'No query provided'}), 400
        
        logger.info(f"🤔 User query: {user_query}")
        logger.info(f"📚 Using collection: {collection_name}")
        
        # Get relevant documents
        logger.info("🔍 Searching for relevant documents...")
        try:
            vector_db = get_vector_store(collection_name)
            search_result = vector_db.similarity_search(query=user_query)
            logger.info(f"📋 Found {len(search_result)} relevant documents")
        except Exception as e:
            logger.error(f"❌ Vector database error: {str(e)}")
            return jsonify({
                'error': f'Unable to access document database. The document may not have been properly indexed. Please try uploading the document again.',
                'details': str(e)
            }), 500
        
        if not search_result:
            logger.warning("⚠️ No relevant documents found")
            return jsonify({
                'error': 'No relevant information found in the document. Please try a different question or re-upload the document.',
                'answer': 'I couldn\'t find any relevant information in the document to answer your question. Please try asking a different question or re-upload the document.'
            }), 404
        
        # Format context
        context = "\n\n\n".join([
            f"Page Content: {result.page_content}\n Page Number: {result.metadata['page_label']}\n File Location: {result.metadata['source']}" 
            for result in search_result
        ])
        
        # Generate response
        logger.info("🤖 Generating AI response...")
        try:
            system_prompt = f"""
You are a helpful assistant that can answer questions based on the given context retrieved from a pdf file along with the page content and page number.

You should only answer the user based on the following context and navigate the user to right page number to know more.

Context:
{context}
"""
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            response = model.generate_content(f"{system_prompt}\n\nUser Question: {user_query}")
            
            logger.info("✅ AI response generated successfully")
            
            return jsonify({
                'answer': response.text,
                'sources': [
                    {
                        'page': result.metadata['page_label'],
                        'content': result.page_content[:200] + '...',
                        'source': result.metadata['source']
                    } for result in search_result
                ]
            })
        except Exception as e:
            logger.error(f"❌ AI generation error: {str(e)}")
            return jsonify({
                'error': 'Unable to generate response. This might be due to API quota limits. Please try again later.',
                'details': str(e)
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {str(e)}")
        return jsonify({'error': f'Chat service error: {str(e)}'}), 500

# Global progress tracking
upload_progress = {
    'status': 'idle',
    'message': '',
    'progress': 0,
    'stage': ''
}

@app.route('/api/progress', methods=['GET'])
def get_progress():
    return jsonify(upload_progress)

def update_progress(status, message, progress=0, stage=''):
    global upload_progress
    upload_progress = {
        'status': status,
        'message': message,
        'progress': progress,
        'stage': stage
    }
    logger.info(f"📊 Progress Update: {status} - {message} ({progress}%)")

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5010))
    app.run(host='0.0.0.0', port=port)
