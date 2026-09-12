from __future__ import annotations

"""
DocMind Second Brain — Database Models & Data Transfer Objects
Defines structured classes and Pydantic validation models for the relational store.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ----------------------------------------------------
# 1. User Model
# ----------------------------------------------------
class UserModel(BaseModel):
    id: str = "default_user"
    email: str = "learner@docmind.local"
    display_name: str = "CS Learner"
    created_at: Optional[str] = None


# ----------------------------------------------------
# 2. Document & Version Models
# ----------------------------------------------------
class DocumentModel(BaseModel):
    id: str
    user_id: str = "default_user"
    filename: str
    original_path: str
    file_hash: str
    folder: str = "General"
    file_size: int = 0
    mime_type: str = "application/pdf"
    status: str = "ACTIVE"  # ACTIVE, SUPERSEDED, ARCHIVED, DELETED
    chunk_count: int = 0
    created_at: Optional[str] = None


class DocumentVersionModel(BaseModel):
    id: str
    document_id: str
    version_number: int = 1
    file_hash: str
    change_summary: Optional[str] = None
    status: str = "ACTIVE"
    created_at: Optional[str] = None


class DocumentChunkModel(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    page_number: int = 1
    section_title: Optional[str] = None
    text_content: str
    token_count: int = 0
    created_at: Optional[str] = None


# ----------------------------------------------------
# 3. Wiki Knowledge Graph Models
# ----------------------------------------------------
class KnowledgeNodeModel(BaseModel):
    id: str
    name: str
    category: str = "CONCEPT"  # CONCEPT, TOPIC, ENTITY, DEFINITION
    summary: str
    canonical_definition: Optional[str] = None
    status: str = "ACTIVE"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KnowledgeRelationshipModel(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    relation_type: str = "RELATES_TO"  # RELATES_TO, IS_A, CAUSES, DEPENDS_ON, SHARES_FOUNDATION
    confidence: float = 1.0
    description: Optional[str] = None
    source_name: Optional[str] = None
    target_name: Optional[str] = None


class KnowledgeSourceModel(BaseModel):
    id: str
    node_id: str
    document_id: str
    document_name: Optional[str] = None
    page_number: int = 1
    snippet: str = ""


# ----------------------------------------------------
# 4. Persistent Memory Models
# ----------------------------------------------------
class MemoryCategory:
    USER_PREFERENCE = "USER_PREFERENCE"
    LEARNING_PREFERENCE = "LEARNING_PREFERENCE"
    PROJECT_CONTEXT = "PROJECT_CONTEXT"
    DOCUMENT_CONTEXT = "DOCUMENT_CONTEXT"
    CONVERSATION_CONTEXT = "CONVERSATION_CONTEXT"
    USER_GOAL = "USER_GOAL"
    LONG_TERM_INFO = "LONG_TERM_INFO"
    DECISION_HISTORY = "DECISION_HISTORY"

    ALL = [
        USER_PREFERENCE,
        LEARNING_PREFERENCE,
        PROJECT_CONTEXT,
        DOCUMENT_CONTEXT,
        CONVERSATION_CONTEXT,
        USER_GOAL,
        LONG_TERM_INFO,
        DECISION_HISTORY,
    ]


class MemoryModel(BaseModel):
    id: str
    user_id: str = "default_user"
    category: str = "USER_PREFERENCE"
    memory_key: str
    memory_value: str
    importance_score: float = 0.5
    project_id: str = "DEFAULT"
    last_accessed_at: Optional[str] = None
    created_at: Optional[str] = None
    score: Optional[float] = None  # Runtime calculated MemoryScore


# ----------------------------------------------------
# 5. Output Artifact Models
# ----------------------------------------------------
class OutputArtifactModel(BaseModel):
    id: str
    user_id: str = "default_user"
    output_type: str = "STUDY_NOTES"  # SUMMARY, STUDY_NOTES, REPORT, QUIZ, FLASHCARDS
    title: str
    file_path: str
    content_preview: Optional[str] = None
    created_at: Optional[str] = None
