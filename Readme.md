 Introduction
This is a comprehensive test document for the RAG (Retrieval-Augmented Generation) system. The system allows users to upload PDF documents and ask intelligent questions about their contents.

 Key Features
The RAG system includes several important features:
- PDF upload and processing with drag-and-drop interface
- Real-time progress tracking during document indexing
- Vector embeddings creation using Google Gemini
- Qdrant vector database for efficient storage and retrieval
- Intelligent question answering with source citations
- Automatic file cleanup after processing

 How It Works
The system follows these steps:
1. User uploads a PDF document through the web interface
2. The PDF is processed and text is extracted
3. Text is chunked into smaller, manageable pieces
4. Each chunk is converted into a vector embedding
5. Vectors are stored in Qdrant vector database
6. When users ask questions, relevant chunks are retrieved
7. The language model generates answers based on retrieved context

 Benefits
This system provides several benefits:
- Accurate answers based on actual document content
- Source citations for verification and trust
- Ability to handle large documents efficiently
- Real-time question answering capabilities
- Professional user interface with progress tracking
- Secure file handling with automatic cleanup

 Technical Architecture
The system uses modern technologies:
- Flask backend with REST API endpoints
- React-like frontend with vanilla JavaScript
- Google Gemini for embeddings and generation
- Qdrant for vector storage and similarity search
- Real-time progress tracking with WebSocket-like polling


