from __future__ import annotations

"""
DocMind Second Brain — Retrieval REST API Router
Exposes unified hybrid search across Vector DB, Wiki Graph, and Persistent Memories.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.embedder import embed_query
from core.vector_store import query as vector_query
from backend.knowledge.graph_service import find_connected_concepts
from backend.memory.memory_manager import retrieve_relevant_memories
from backend.orchestration.context_assembler import assemble_grounded_context
from config import TOP_K

router = APIRouter(prefix="", tags=["Retrieval"])


class RetrieveRequest(BaseModel):
    query: str
    folder: Optional[str] = None
    top_k: int = TOP_K


class HybridSearchRequest(BaseModel):
    query: str
    folder: Optional[str] = None
    user_id: str = "default_user"
    active_project: str = "DEFAULT"
    include_wiki: bool = True
    include_memory: bool = True


@router.post("/retrieve")
def retrieve_chunks(req: RetrieveRequest):
    """Retrieves verbatim chunks from the Vector Database."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    query_emb = embed_query(req.query)
    target_folders = [req.folder] if req.folder and req.folder.lower() not in ("all", "*") else None

    results = vector_query(query_emb, top_k=req.top_k, folder=target_folders)
    return {
        "chunks": results.get("chunks", []),
        "metadatas": results.get("metadatas", []),
        "distances": results.get("distances", []),
    }


@router.post("/search/hybrid")
def hybrid_search(req: HybridSearchRequest):
    """
    Executes unified hybrid retrieval across:
      1. Vector DB Chunks (Primary Evidence)
      2. Wiki Graph (Concepts & Cross-References)
      3. Persistent Memories (User & Learning Preferences)
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    query_emb = embed_query(req.query)
    target_folders = [req.folder] if req.folder and req.folder.lower() not in ("all", "*") else None
    results = vector_query(query_emb, top_k=TOP_K, folder=target_folders)

    chunks = results.get("chunks", [])
    metadatas = results.get("metadatas", [])

    assembled = assemble_grounded_context(
        query=req.query,
        raw_chunks=chunks,
        metadatas=metadatas,
        user_id=req.user_id,
        active_project=req.active_project,
        include_wiki=req.include_wiki,
        include_memory=req.include_memory,
    )

    return {
        "grounded_context": assembled["context"],
        "sources": assembled["sources"],
        "connected_wiki_concepts": assembled["wiki_concepts"],
        "activated_memories": assembled["activated_memories"],
        "token_budget": assembled["budget_info"],
    }
