# ===========================
# Imports
# ===========================

import chromadb

from utils import (
    load_pdf,
    create_chunks,
    get_gemini_client,
    create_embeddings
)

from config import (
    PDF_FILE,
    CHROMA_PATH,
    COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)


# ===========================
# Create Gemini Client
# ===========================

client = get_gemini_client()


# ===========================
# Read PDF
# ===========================
try:
    text = load_pdf(PDF_FILE)
except FileNotFoundError:
    print(f"Error: '{PDF_FILE}' was not found")
    print(f"Please place the pdf inside the prohect folder")
    exit()

# ===========================
# Split Text into Chunks
# ===========================

chunks = create_chunks(
    text,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)

print(f"Total chunks created: {len(chunks)}")


# ===========================
# Generate Embeddings
# ===========================

embeddings = create_embeddings(
    client,
    chunks
)


# ===========================
# Connect to Persistent ChromaDB
# ===========================

chroma_client = chromadb.PersistentClient(
    path=CHROMA_PATH
)


# ===========================
# Remove Old Collection
# ===========================

try:
    chroma_client.delete_collection(
        name=COLLECTION_NAME
    )

    print("Old collection removed.")

except Exception:
    pass


# ===========================
# Create Fresh Collection
# ===========================

collection = chroma_client.create_collection(
    name=COLLECTION_NAME
)


# ===========================
# Store Chunks + Embeddings
# ===========================

collection.add(
    ids=[
        f"chunk_{i}"
        for i in range(len(chunks))
    ],
    documents=chunks,
    embeddings=embeddings
)


# ===========================
# Finished
# ===========================

print(f"Documents stored: {collection.count()}")
print("PDF indexed successfully!")