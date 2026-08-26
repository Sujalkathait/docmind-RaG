"""
DocMind RAG — PDF Ingestion Module
Handles file upload processing: text extraction, chunking, embedding, and vector storage.
"""

from __future__ import annotations
import os
import time
from typing import List, Any
import streamlit as st

from config import PDF_FOLDER, CHUNK_SIZE, CHUNK_OVERLAP
from core.pdf_loader import load_pdf_from_bytes
from core.chunker import create_chunks
from core.embedder import embed_documents
from core.vector_store import add_document, sanitize_folder_name


def process_pdf_uploads(files: List[Any], folder: str) -> None:
    """Process uploaded PDF files: extract → chunk → embed → store in ChromaDB."""
    if not files:
        return

    progress = st.sidebar.progress(0, text="Starting ingestion...")
    total = len(files)
    success_count = 0

    for i, uploaded_file in enumerate(files):
        filename = uploaded_file.name
        progress.progress((i / total) * 0.1, text=f"Reading {filename}...")

        try:
            pdf_bytes = uploaded_file.read()

            # Save file to disk under specified folder
            clean_folder = sanitize_folder_name(folder)
            folder_path = os.path.join(PDF_FOLDER, clean_folder)
            os.makedirs(folder_path, exist_ok=True)
            save_path = os.path.join(folder_path, filename)
            with open(save_path, "wb") as f:
                f.write(pdf_bytes)

            # Extract text using fitz (PyMuPDF)
            progress.progress((i / total) * 0.3, text=f"Extracting text from {filename}...")
            text = load_pdf_from_bytes(pdf_bytes)

            if not text.strip():
                st.sidebar.warning(f"⚠️ No text extracted from '{filename}', skipping.")
                continue

            # Split into overlapping chunks
            progress.progress((i / total) * 0.5, text=f"Chunking {filename}...")
            chunks = create_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)

            if not chunks:
                st.sidebar.warning(f"⚠️ No chunks created from '{filename}', skipping.")
                continue

            # Generate vector embeddings
            progress.progress(
                (i / total) * 0.7,
                text=f"Embedding {filename} ({len(chunks)} chunks)...",
            )
            embeddings = embed_documents(chunks)

            # Store chunks & embeddings in ChromaDB
            progress.progress((i / total) * 0.9, text=f"Storing {filename} in ChromaDB...")
            add_document(chunks, embeddings, filename, folder=clean_folder)

            success_count += 1

        except Exception as e:
            st.sidebar.error(f"❌ Error processing '{filename}': {e}")

    progress.progress(1.0, text="Indexing complete!")
    time.sleep(0.4)
    progress.empty()

    if success_count > 0:
        st.sidebar.success(f"✅ Indexed {success_count}/{total} PDF(s) into folder '{folder}'")
        st.rerun()
