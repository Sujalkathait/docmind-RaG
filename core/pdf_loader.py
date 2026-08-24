"""
PDF text extraction using PyMuPDF (fitz).
Faster and more robust than pypdf for complex layouts.
"""

import os
import pymupdf as fitz  # PyMuPDF


def load_pdf(pdf_path: str) -> str:
    """
    Reads a PDF file and returns all its text as a single string.
    Handles encrypted PDFs, image-only pages, and complex layouts.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        if page_text and page_text.strip():
            text_parts.append(page_text)

    doc.close()
    return "\n\n".join(text_parts)


def load_pdf_pages(pdf_path: str) -> list[dict]:
    """
    Reads a PDF and returns per-page text with metadata.
    Useful for source attribution in RAG responses.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        pages.append({
            "page_number": page_num + 1,
            "text": page_text.strip() if page_text else "",
            "has_text": bool(page_text and page_text.strip()),
        })

    doc.close()
    return pages


def load_pdf_from_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts text from in-memory PDF bytes (for upload handling).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        if page_text and page_text.strip():
            text_parts.append(page_text)

    doc.close()
    return "\n\n".join(text_parts)
