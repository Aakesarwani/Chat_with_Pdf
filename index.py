from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# 🔐 Load environment variables
load_dotenv()

# 1️⃣ LOAD PDF
pdf_path = Path(__file__).parent / "javascript_tutorial.pdf"
loader = PyPDFLoader(file_path=pdf_path)
docs = loader.load()

# 2️⃣ CHUNKING
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = text_splitter.split_documents(docs)

# 3️⃣ GEMINI EMBEDDINGS
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

# 4️⃣ CREATE QDRANT CLIENT AND COLLECTION
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

collection_name = "chat_with_pdf"

# Check if collection exists, if not create it
try:
    qdrant_client.get_collection(collection_name)
    print(f"Collection '{collection_name}' already exists")
    # Delete and recreate with correct dimensions
    qdrant_client.delete_collection(collection_name)
    print(f"Deleted existing collection '{collection_name}'")
except:
    print(f"Collection '{collection_name}' doesn't exist, creating new one")

print(f"Creating collection '{collection_name}' with 3072 dimensions")
qdrant_client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=3072, distance=Distance.COSINE)
)
#Fixed vector dimensions to match embedding output (3072)

# 5️⃣ CREATE VECTOR STORE AND ADD DOCUMENTS
vector_store = Qdrant(
    client=qdrant_client,
    collection_name=collection_name,
    embeddings=embeddings
)

# Add documents to the collection in batches
batch_size = 5  # Added batch processing with rate limiting
total_chunks = len(chunks)
print(f"Adding {total_chunks} chunks to Qdrant in batches of {batch_size}...")

import time

for i in range(0, total_chunks, batch_size):
    batch = chunks[i:i + batch_size]
    batch_num = i//batch_size + 1
    total_batches = (total_chunks + batch_size - 1)//batch_size
    print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")
    
    try:
        vector_store.add_documents(batch)
        print(f"✅ Batch {batch_num} completed")
        
        # Add delay to avoid rate limiting 
        if batch_num < total_batches:
            print("Waiting 2 seconds to avoid rate limiting...")
            time.sleep(2)
            
    except Exception as e:
        print(f"❌ Error in batch {batch_num}: {e}")
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            print("Rate limit hit. Waiting 30 seconds before retrying...")
            time.sleep(30)
            # Retry the batch
            try:
                vector_store.add_documents(batch)
                print(f"✅ Batch {batch_num} completed after retry")
            except Exception as retry_e:
                print(f"❌ Retry failed for batch {batch_num}: {retry_e}")
                break
        else:
            break

print("✅ Indexing completed. Data stored in Qdrant.")