
# Imports
import chromadb

from utils import (
    get_gemini_client,
    create_query_embedding
)

from config import (
    GEMINI_MODEL,
    CHROMA_PATH,
    COLLECTION_NAME,
    TOP_K
)

# Gemini Client

client = get_gemini_client()


# Connect to Persistent ChromaDB

chroma_client = chromadb.PersistentClient(
    path="chroma_db"
)


# Open Existing Collection

try:
    collection = chroma_client.get_collection(
    name=COLLECTION_NAME
)

except Exception:
    print("vector database not found")
    print("please eun 'python index.py' first")
    exit()

print("=" * 50)
print("📄 PDF RAG Chatbot")
print("Type 'exit' to quit")
print("=" * 50)


while True:

    # -----------------------
    # User Input
    # -----------------------

    question = input("\nAsk your question: ")

    if question.lower() == "exit":
        print("\n👋 Goodbye!")
        break

    if not question.strip():
        print("please enter a valid question.")
        continue


# Generate Query Embedding

    query_embedding = create_query_embedding(
        client,
        question
)



# Search Similar Chunks

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K
    )


    # Extract Retrieved Chunks

    retrieved_chunks = results["documents"][0]


    # Build Context

    context = "\n\n".join(retrieved_chunks)

    # ===========================
    # Build Prompt

    prompt = f"""
    You are a helpful AI assistant.

    Answer the user's question ONLY using the provided context.

    If the answer is not available in the context, say:
    "I couldn't find the answer in the provided document."

    Context:
    {context}

    Question:
    {question}

    Answer:
    """


# Generate Answer

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )


    # Display Answer
    print("\nAnswer:\n")
    print("=" * 50)
    print(response.text)