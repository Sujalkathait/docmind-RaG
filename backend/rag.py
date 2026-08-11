import chromadb

from utils import (
    get_gemini_client,
    create_query_embedding
)

from config import (
    GEMINI_MODEL,
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
collection = chroma_client.get_collection(
    name=COLLECTION_NAME
)


def ask_question(question: str):

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

    return response.text