from __future__ import annotations

from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL, QUERY_PREFIX

# Singleton model instance
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazily loads and caches the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_documents(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Generates embeddings for a list of document chunks.
    Documents do NOT get the query prefix — BGE treats them as passages.
    """
    if not texts:
        return []

    model = _get_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return [emb.tolist() for emb in embeddings]


def embed_query(text: str) -> list[float]:
    """
    Generates an embedding for a single query.
    BGE-small-en-v1.5 uses a query instruction prefix for better retrieval.
    """
    if not text or not text.strip():
        text = " "

    model = _get_model()
    query_text = QUERY_PREFIX + text
    embedding = model.encode(
        query_text,
        normalize_embeddings=True,
    )
    return embedding.tolist()
