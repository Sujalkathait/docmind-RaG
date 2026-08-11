import os
import tempfile

import chromadb

from utils import (
    load_pdf,
    create_chunks,
    get_gemini_client,
    create_embeddings
)

from config import (
    CHROMA_PATH,
    COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)


def process_uploaded_pdf(pdf_file):
    """
    Process an uploaded PDF and store its
    chunks + embeddings in ChromaDB.
    """

    # ---------------------------------
    # Save uploaded PDF temporarily
    # ---------------------------------

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as temp_file:

        temp_file.write(pdf_file)

        temp_pdf_path = temp_file.name


    try:

        # ---------------------------------
        # Extract text
        # ---------------------------------

        text = load_pdf(temp_pdf_path)


        if not text.strip():

            raise ValueError(
                "Could not extract any text from the PDF."
            )


        # ---------------------------------
        # Create chunks
        # ---------------------------------

        chunks = create_chunks(
            text,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )


        if not chunks:

            raise ValueError(
                "No text chunks could be created from the PDF."
            )


        # ---------------------------------
        # Create Gemini client
        # ---------------------------------

        client = get_gemini_client()


        # ---------------------------------
        # Generate embeddings
        # ---------------------------------

        embeddings = create_embeddings(
            client,
            chunks
        )


        # ---------------------------------
        # Connect to ChromaDB
        # ---------------------------------

        chroma_client = chromadb.PersistentClient(
            path=CHROMA_PATH
        )


        # ---------------------------------
        # Get existing collection
        # ---------------------------------

        collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME
        )


        # ---------------------------------
        # Remove previous document
        # ---------------------------------

        existing_data = collection.get()

        existing_ids = existing_data.get("ids", [])


        if existing_ids:

            collection.delete(
                ids=existing_ids
            )


        # ---------------------------------
        # Store new document
        # ---------------------------------

        collection.add(

            ids=[
                f"chunk_{i}"
                for i in range(len(chunks))
            ],

            documents=chunks,

            embeddings=embeddings,

            metadatas=[
                {
                    "source": "uploaded_pdf"
                }
                for _ in chunks
            ]
        )


        return {
            "success": True,
            "chunks": len(chunks)
        }


    finally:

        # ---------------------------------
        # Delete temporary PDF
        # ---------------------------------

        if os.path.exists(temp_pdf_path):

            os.remove(temp_pdf_path)