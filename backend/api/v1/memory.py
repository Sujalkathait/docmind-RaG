from __future__ import annotations

"""
DocMind Second Brain — Memory REST API Router
Endpoints for managing persistent preferences, learning goals, and context history.
"""

import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.database.crud import (
    list_memories,
    get_memory,
    upsert_memory,
    delete_memory,
    clear_all_memories,
)
from backend.database.models import MemoryModel, MemoryCategory

router = APIRouter(prefix="/memory", tags=["Memory"])


class CreateMemoryRequest(BaseModel):
    user_id: str = "default_user"
    category: str = MemoryCategory.USER_PREFERENCE
    key: Optional[str] = None
    value: Optional[str] = None
    content: Optional[str] = None
    importance_score: float = 0.7
    project_id: str = "DEFAULT"


class UpdateMemoryRequest(BaseModel):
    value: Optional[str] = None
    content: Optional[str] = None
    importance_score: Optional[float] = None
    project_id: Optional[str] = None


@router.get("", response_model=List[MemoryModel])
def get_memories(user_id: str = "default_user", category: Optional[str] = None):
    """Lists all stored persistent memories for a user."""
    return list_memories(user_id=user_id, category=category)


@router.post("", response_model=MemoryModel, status_code=status.HTTP_201_CREATED)
def create_memory_endpoint(req: CreateMemoryRequest):
    """Creates or updates a persistent memory item."""
    val = (req.value or req.content or "").strip()
    if not val:
        raise HTTPException(status_code=400, detail="Memory content/value cannot be empty.")

    key = req.key
    if not key or not key.strip():
        # Auto-generate a clean descriptive key
        words = "".join([c if c.isalnum() else "_" for c in val[:30].strip()]).strip("_")
        key = f"{req.category.lower()}_{words}_{int(time.time())}"

    mem = upsert_memory(
        user_id=req.user_id,
        category=req.category,
        key=key,
        value=val,
        importance_score=req.importance_score,
        project_id=req.project_id,
    )
    return mem


@router.patch("/{memory_id}", response_model=MemoryModel)
def update_memory_endpoint(memory_id: str, req: UpdateMemoryRequest):
    """Modifies an existing memory record."""
    mem = get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory record not found.")

    val = req.value if req.value is not None else mem.memory_value
    imp = req.importance_score if req.importance_score is not None else mem.importance_score
    proj = req.project_id if req.project_id is not None else mem.project_id

    updated = upsert_memory(
        user_id=mem.user_id,
        category=mem.category,
        key=mem.memory_key,
        value=val,
        importance_score=imp,
        project_id=proj,
    )
    return updated


@router.delete("/{memory_id}")
def delete_memory_endpoint(memory_id: str):
    """Deletes a single memory by ID."""
    success = delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory record not found.")
    return {"deleted": True, "memory_id": memory_id}


@router.delete("")
def clear_memories_endpoint(user_id: str = "default_user"):
    """Wipes all persistent memories for user."""
    count = clear_all_memories(user_id=user_id)
    return {"cleared": True, "count": count}
