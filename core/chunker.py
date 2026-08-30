from __future__ import annotations

"""
Text chunking using RecursiveCharacterTextSplitter.
Chunk sizes tuned for BGE-small-en-v1.5's 512-token window.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter



def create_chunks(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[str]:
    """
    Splits text into overlapping chunks for embedding and retrieval.
    Uses recursive splitting on paragraph → sentence → word boundaries.
    """
    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_text(text)
    return [c for c in chunks if c.strip()]
