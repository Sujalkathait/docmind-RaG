from __future__ import annotations

"""
DocMind Second Brain — Documents REST API Router
Endpoints for uploading, listing, inspecting, and deleting raw source documents.
"""

import os
import hashlib
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel

from backend.database.crud import (
    create_document,
    get_document_by_id,
    list_documents,
    delete_document as db_delete_document,
    add_document_chunks,
    list_folders,
)
from backend.database.models import DocumentModel
from core.pdf_loader import load_pdf_from_bytes, load_pdf_pages
from core.chunker import create_chunks
from core.embedder import embed_documents
from core.vector_store import add_document as chroma_add_document, delete_document as chroma_delete_document
from backend.knowledge.concept_miner import extract_concepts_from_text
from backend.knowledge.relationship_builder import auto_build_cross_document_links
from config import CHUNK_SIZE, CHUNK_OVERLAP

router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_indexed: int
    concepts_discovered: int
    folder: str
    status: str = "ACTIVE"


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
@router.post("/upload/", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    folder: str = Form("General"),
    user_id: str = Form("default_user"),
):
    """
    Ingests a raw document into Second Brain vault (raw/pdfs), extracts text,
    indexes chunks into ChromaDB and SQLite, and mines concepts into the Wiki.
    """
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith((".pdf", ".txt", ".md")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload PDF, TXT, or Markdown documents.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    # Compute SHA-256 Hash
    file_hash = hashlib.sha256(content).hexdigest()
    doc_id = f"doc_{file_hash[:16]}"

    # Save to raw/pdfs vault
    raw_dir = os.path.join("raw", "pdfs")
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, f"{doc_id}_{filename}")
    with open(raw_path, "wb") as f:
        f.write(content)

    # Extract text
    extracted_text = load_pdf_from_bytes(content)
    if not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No digital text could be extracted. The document may be an un-OCRed scan.",
        )

    # Save extracted JSON in raw/extracted
    extracted_dir = os.path.join("raw", "extracted")
    os.makedirs(extracted_dir, exist_ok=True)
    with open(os.path.join(extracted_dir, f"{doc_id}.txt"), "w", encoding="utf-8") as f:
        f.write(extracted_text)

    # Chunk text
    chunks = create_chunks(extracted_text, CHUNK_SIZE, CHUNK_OVERLAP)
    if not chunks:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No chunks created.")

    # Embed and store in ChromaDB
    embeddings = embed_documents(chunks)
    chroma_add_document(chunks, embeddings, filename, folder=folder)

    # Register in SQLite
    create_document(
        doc_id=doc_id,
        filename=filename,
        original_path=raw_path,
        file_hash=file_hash,
        folder=folder,
        file_size=len(content),
        mime_type="application/pdf",
        user_id=user_id,
    )
    add_document_chunks(document_id=doc_id, chunks=chunks)

    # Mine concepts into Wiki
    discovered_concepts = extract_concepts_from_text(extracted_text, document_id=doc_id, page_number=1)
    auto_build_cross_document_links()

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=filename,
        chunks_indexed=len(chunks),
        concepts_discovered=len(discovered_concepts),
        folder=folder,
        status="ACTIVE",
    )


@router.get("", response_model=List[DocumentModel])
@router.get("/", response_model=List[DocumentModel])
def get_documents(folder: Optional[str] = None, user_id: str = "default_user"):
    """Lists all active indexed documents."""
    return list_documents(user_id=user_id, folder=folder)


@router.get("/folders")
@router.get("/folders/")
@router.get("/folders/list")
@router.get("/folders/list/")
def get_folders_list(user_id: str = "default_user"):
    """Lists all available collection folders."""
    return {"folders": list_folders(user_id=user_id)}


@router.get("/{doc_id}", response_model=DocumentModel)
def get_document(doc_id: str):
    """Fetches details of a specific document."""
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {doc_id} not found.")
    return doc


@router.delete("/{doc_id}")
def delete_document_endpoint(doc_id: str):
    """Deletes a document and cascades deletion through SQLite and ChromaDB."""
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Delete from ChromaDB
    chroma_delete_document(doc.filename, folder=doc.folder)

    # Delete from SQLite
    db_delete_document(doc_id)

    # Delete physical raw file if exists
    if os.path.exists(doc.original_path):
        try:
            os.remove(doc.original_path)
        except Exception:
            pass

    return {"deleted": True, "document_id": doc_id}
