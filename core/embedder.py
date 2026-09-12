from __future__ import annotations

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from functools import lru_cache
from sentence_transformers import SentenceTransformer

try:
    import torch
    # Set PyTorch CPU threads to avoid contention with llama-cpp
    torch.set_num_threads(min(4, os.cpu_count() or 4))
except Exception:
    pass

from config import EMBEDDING_MODEL, QUERY_PREFIX

# Singleton model instance
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazily loads and caches the embedding model in memory."""
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


@lru_cache(maxsize=512)
def _cached_embed_query(query_text: str) -> tuple[float, ...]:
    """LRU-cached single query embedding computation."""
    model = _get_model()
    embedding = model.encode(
        query_text,
        normalize_embeddings=True,
    )
    return tuple(float(x) for x in embedding)


def embed_query(text: str) -> list[float]:
    """
    Generates or retrieves cached embedding for a single query.
    BGE-small-en-v1.5 uses a query instruction prefix for optimal retrieval.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        cleaned = " "
    query_text = QUERY_PREFIX + cleaned
    return list(_cached_embed_query(query_text))


def clear_query_cache() -> None:
    """Clears the query embedding LRU cache."""
    _cached_embed_query.cache_clear()
