from __future__ import annotations

import os
try:
    import fitz  # PyMuPDF
except ImportError:
    import pymupdf as fitz  # type: ignore



def load_pdf(pdf_path: str) -> str:
    """
    Reads a PDF file and returns all its text as a single string.
    Handles encrypted PDFs, image-only pages, and complex layouts.
    Uses sort=True for natural reading order.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    text_parts = []
    with fitz.open(pdf_path) as doc:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text("text", sort=True)
            if page_text and page_text.strip():
                text_parts.append(page_text.strip())

    return "\n\n".join(text_parts)


def load_pdf_pages(pdf_path: str) -> list[dict]:
    """
    Reads a PDF and returns per-page text with metadata.
    Useful for source attribution in RAG responses.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []
    with fitz.open(pdf_path) as doc:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text("text", sort=True)
            pages.append({
                "page_number": page_num + 1,
                "text": page_text.strip() if page_text else "",
                "has_text": bool(page_text and page_text.strip()),
            })

    return pages


def load_pdf_from_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts text from in-memory PDF bytes (for upload handling).
    Ensures safe resource closing and natural reading order.
    """
    if not pdf_bytes:
        return ""

    text_parts = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text("text", sort=True)
            if page_text and page_text.strip():
                text_parts.append(page_text.strip())

    return "\n\n".join(text_parts)

