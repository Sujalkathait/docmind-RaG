from __future__ import annotations

"""
DocMind Second Brain — Memory Scoring Engine
Calculates normalized compound memory scores based on:
  MemoryScore = 0.45*Relevance + 0.25*Importance + 0.15*Recency + 0.15*ProjectMatch
"""

import math
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

W_RELEVANCE = 0.45
W_IMPORTANCE = 0.25
W_RECENCY = 0.15
W_PROJECT = 0.15

# Recency decay rate: lambda = 0.05 per day (half-life ~ 14 days)
RECENCY_LAMBDA = 0.05


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    val = dot / (norm1 * norm2)
    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, (val + 1.0) / 2.0))


def compute_recency_score(last_accessed_iso_or_ts: Optional[str | float]) -> float:
    """
    Computes time decay score S_rec in [0.0, 1.0] using exponential decay:
    S_rec = e^(-lambda * delta_days)
    """
    if not last_accessed_iso_or_ts:
        return 0.5

    now_ts = time.time()
    try:
        if isinstance(last_accessed_iso_or_ts, (int, float)):
            delta_sec = max(0.0, now_ts - float(last_accessed_iso_or_ts))
        else:
            # Parse ISO string like '2026-09-12 02:40:00'
            dt = datetime.fromisoformat(str(last_accessed_iso_or_ts).replace("Z", ""))
            delta_sec = max(0.0, now_ts - dt.timestamp())
        
        delta_days = delta_sec / 86400.0
        return math.exp(-RECENCY_LAMBDA * delta_days)
    except Exception:
        return 0.5


def compute_memory_score(
    relevance_score: float,
    importance_score: float,
    last_accessed: Optional[str | float],
    memory_project_id: str = "DEFAULT",
    active_project_id: str = "DEFAULT",
) -> float:
    """
    Computes the compound MemoryScore:
      MemoryScore = 0.45 * S_rel + 0.25 * S_imp + 0.15 * S_rec + 0.15 * S_proj
    """
    s_rel = max(0.0, min(1.0, relevance_score))
    s_imp = max(0.0, min(1.0, importance_score))
    s_rec = compute_recency_score(last_accessed)
    s_proj = 1.0 if (memory_project_id == active_project_id) else 0.0

    score = (
        W_RELEVANCE * s_rel
        + W_IMPORTANCE * s_imp
        + W_RECENCY * s_rec
        + W_PROJECT * s_proj
    )
    return round(score, 4)
