from __future__ import annotations
import os
import time
import hashlib
from typing import List, Any
import streamlit as st

from config import PDF_FOLDER, CHUNK_SIZE, CHUNK_OVERLAP
from core.pdf_loader import load_pdf_from_bytes
from core.chunker import create_chunks
from core.embedder import embed_documents
from core.vector_store import add_document, sanitize_folder_name
from backend.database.crud import create_document, add_document_chunks
from backend.knowledge.concept_miner import extract_concepts_from_text
from backend.knowledge.relationship_builder import auto_build_cross_document_links


def process_pdf_uploads(files: List[Any], folder: str) -> None:
    """Process uploaded PDF files: raw vault → extract → chunk → embed → ChromaDB → SQLite & Wiki."""
    if not files:
        return

    progress = st.sidebar.progress(0.0, text="Starting ingestion...")
    total = len(files)
    success_count = 0
    total_concepts_discovered = 0

    for i, uploaded_file in enumerate(files):
        filename = getattr(uploaded_file, "name", "document.pdf")
        base_progress = i / total
        file_weight = 1.0 / total

        progress.progress(min(1.0, base_progress + file_weight * 0.1), text=f"Reading {filename}...")

        try:
            # Ensure file pointer is at the beginning
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            pdf_bytes = uploaded_file.read()

            if not pdf_bytes:
                st.sidebar.warning(f"⚠️ '{filename}' is empty, skipping.")
                continue

            # Compute SHA-256 for Second Brain immutability
            file_hash = hashlib.sha256(pdf_bytes).hexdigest()
            doc_id = f"doc_{file_hash[:16]}"

            # 1. Save file to disk under specified folder (existing RAG)
            clean_folder = sanitize_folder_name(folder)
            folder_path = os.path.join(PDF_FOLDER, clean_folder)
            os.makedirs(folder_path, exist_ok=True)
            save_path = os.path.join(folder_path, filename)
            with open(save_path, "wb") as f:
                f.write(pdf_bytes)

            # 2. Second Brain: Save immutable original in raw/pdfs/
            raw_vault_dir = os.path.join("raw", "pdfs")
            os.makedirs(raw_vault_dir, exist_ok=True)
            raw_vault_path = os.path.join(raw_vault_dir, f"{doc_id}_{filename}")
            with open(raw_vault_path, "wb") as f:
                f.write(pdf_bytes)

            # 3. Extract text using PyMuPDF (fitz)
            progress.progress(min(1.0, base_progress + file_weight * 0.3), text=f"Extracting text from {filename}...")
            text = load_pdf_from_bytes(pdf_bytes)

            if not text.strip():
                st.sidebar.warning(f"⚠️ No readable digital text extracted from '{filename}' (may be scanned image).")
                continue

            # Second Brain: Save extracted clean text
            extracted_dir = os.path.join("raw", "extracted")
            os.makedirs(extracted_dir, exist_ok=True)
            with open(os.path.join(extracted_dir, f"{doc_id}.txt"), "w", encoding="utf-8") as f:
                f.write(text)

            # 4. Split into overlapping chunks
            progress.progress(min(1.0, base_progress + file_weight * 0.5), text=f"Chunking {filename}...")
            chunks = create_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)

            if not chunks:
                st.sidebar.warning(f"⚠️ No chunks created from '{filename}', skipping.")
                continue

            # 5. Generate vector embeddings
            progress.progress(
                min(1.0, base_progress + file_weight * 0.7),
                text=f"Embedding {filename} ({len(chunks)} chunks)...",
            )
            embeddings = embed_documents(chunks)

            # 6. Store chunks & embeddings in ChromaDB
            progress.progress(min(1.0, base_progress + file_weight * 0.85), text=f"Indexing {filename} in ChromaDB...")
            add_document(chunks, embeddings, filename, folder=clean_folder)

            # 7. Second Brain: Register in SQLite database
            create_document(
                doc_id=doc_id,
                filename=filename,
                original_path=raw_vault_path,
                file_hash=file_hash,
                folder=clean_folder,
                file_size=len(pdf_bytes),
            )
            add_document_chunks(document_id=doc_id, chunks=chunks)

            # 8. Second Brain: Mine concepts into Wiki
            progress.progress(min(1.0, base_progress + file_weight * 0.95), text=f"Mining Wiki concepts from {filename}...")
            mined = extract_concepts_from_text(text, document_id=doc_id, page_number=1)
            total_concepts_discovered += len(mined)

            success_count += 1

        except Exception as e:
            st.sidebar.error(f"❌ Error processing '{filename}': {e}")

    # Build cross-document links
    if success_count > 0:
        auto_build_cross_document_links()

    progress.progress(1.0, text="Indexing complete!")
    time.sleep(0.4)
    progress.empty()

    if success_count > 0:
        extra_info = f" ({total_concepts_discovered} Wiki concepts mined)" if total_concepts_discovered > 0 else ""
        st.sidebar.success(f"✅ Indexed {success_count}/{total} PDF(s) into '{folder}'{extra_info}")
        st.rerun()


