from __future__ import annotations

"""
DocMind Second Brain — Memory Manager
Handles selective retrieval, scoring, ranking, and budget allocation for persistent memories.
"""

from typing import List, Optional, Dict, Any
from backend.database.crud import (
    list_memories,
    upsert_memory,
    delete_memory,
    clear_all_memories,
    touch_memory_accessed,
)
from backend.database.models import MemoryModel, MemoryCategory
from backend.memory.scoring import compute_memory_score, cosine_similarity
from core.embedder import embed_query

# Constants
MIN_MEMORY_SCORE = 0.40  # Threshold floor to eliminate irrelevant context
MAX_MEMORY_TOKENS = 120  # Strict budget ceiling for prompt injection


def retrieve_relevant_memories(
    user_id: str = "default_user",
    query: str = "",
    active_project: str = "DEFAULT",
    top_k: int = 2,
    min_score: float = MIN_MEMORY_SCORE,
) -> List[MemoryModel]:
    """
    Ranks stored memories against user query using compound MemoryScore:
      MemoryScore = 0.45*Rel + 0.25*Imp + 0.15*Rec + 0.15*Proj
    Enforces threshold floor (min_score) and token ceiling (<=120 tokens).
    """
    all_memories = list_memories(user_id=user_id)
    if not all_memories:
        return []

    # If query is provided, compute query embedding
    query_emb: Optional[List[float]] = None
    if query and query.strip():
        try:
            query_emb = embed_query(query)
        except Exception:
            query_emb = None

    scored_memories: List[MemoryModel] = []

    for mem in all_memories:
        # Calculate semantic relevance
        if query_emb is not None:
            # Memory text representation for embedding comparison
            mem_text = f"{mem.category} {mem.memory_key}: {mem.memory_value}"
            try:
                mem_emb = embed_query(mem_text)
                relevance = cosine_similarity(query_emb, mem_emb)
            except Exception:
                relevance = 0.5
        else:
            relevance = 0.5

        final_score = compute_memory_score(
            relevance_score=relevance,
            importance_score=mem.importance_score,
            last_accessed=mem.last_accessed_at,
            memory_project_id=mem.project_id,
            active_project_id=active_project,
        )

        mem.score = final_score

        if final_score >= min_score:
            scored_memories.append(mem)

    # Sort descending by computed score
    scored_memories.sort(key=lambda m: (m.score or 0.0), reverse=True)

    # Take top_k candidates and enforce token limit
    selected: List[MemoryModel] = []
    total_tokens = 0

    for mem in scored_memories[:top_k]:
        est_tokens = len(mem.memory_value) // 4 + 8
        if total_tokens + est_tokens <= MAX_MEMORY_TOKENS:
            selected.append(mem)
            total_tokens += est_tokens
            touch_memory_accessed(mem.id)

    return selected


def add_user_preference(
    key: str,
    value: str,
    user_id: str = "default_user",
    importance: float = 0.8,
) -> MemoryModel:
    """Helper to save a core user preference."""
    return upsert_memory(
        user_id=user_id,
        category=MemoryCategory.USER_PREFERENCE,
        key=key,
        value=value,
        importance_score=importance,
    )


def add_learning_preference(
    key: str,
    value: str,
    user_id: str = "default_user",
    importance: float = 0.9,
) -> MemoryModel:
    """Helper to save a cognitive learning preference."""
    return upsert_memory(
        user_id=user_id,
        category=MemoryCategory.LEARNING_PREFERENCE,
        key=key,
        value=value,
        importance_score=importance,
    )


def remove_memory(memory_id: str) -> bool:
    """Removes a single memory."""
    return delete_memory(memory_id)


def reset_memories(user_id: str = "default_user") -> int:
    """Wipes all memories for a user."""
    return clear_all_memories(user_id)
