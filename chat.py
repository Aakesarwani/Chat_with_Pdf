# retrieval pipeline

from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
import google.generativeai as genai

load_dotenv()


embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

vector_db=QdrantVectorStore.from_existing_collection(
    embedding=embeddings,
    collection_name="chat_with_pdf",
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

#Take user input
user_query = input("Ask something: ")

# Returns relevant chunks from vector db
search_result=vector_db.similarity_search(query=user_query)
print(search_result)


context = "\n\n\n".join([f"Page Content: {result.page_content}\n Page Number: {result.metadata['page_label']}\n File Location: {result.metadata['source']}" 
for result in search_result])

# Prompt
SYSTEM_PROMPT=f"""
You are a helpful assistant that can answer questions based on the given context retrieved from a pdf file along with the page content and page number.

You should only answer the user based on the following context and navigate the user to right page number to know more.

Context:
{context}
"""


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-2.5-flash')
response = model.generate_content(f"{SYSTEM_PROMPT}\n\nUser Question: {user_query}")

print(response.text)