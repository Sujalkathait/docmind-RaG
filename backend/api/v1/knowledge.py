from __future__ import annotations

"""
DocMind Second Brain — Knowledge REST API Router
Endpoints for querying Wiki concepts, definitions, relationships, and graph structure.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.database.crud import (
    list_knowledge_nodes,
    get_knowledge_node,
    upsert_knowledge_node,
    get_node_relationships,
    get_sources_for_node,
    add_knowledge_relationship,
)
from backend.database.models import (
    KnowledgeNodeModel,
    KnowledgeRelationshipModel,
    KnowledgeSourceModel,
)
from backend.knowledge.graph_service import get_full_graph_for_ui

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


class CreateConceptRequest(BaseModel):
    name: str
    category: str = "CONCEPT"
    summary: str
    canonical_definition: Optional[str] = None


class AddRelationshipRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    relation_type: str = "RELATES_TO"
    confidence: float = 1.0
    description: Optional[str] = None


@router.get("", response_model=List[KnowledgeNodeModel])
@router.get("/concepts", response_model=List[KnowledgeNodeModel])
def get_knowledge_nodes(category: Optional[str] = None, search: Optional[str] = None):
    """Queries Wiki concepts with optional category filter or text search."""
    return list_knowledge_nodes(category=category, query=search)


@router.get("/graph")
@router.get("/graph/full")
def get_full_graph():
    """Returns complete node and edge graph for frontend visualization."""
    return get_full_graph_for_ui()


@router.post("/mine/{doc_id}")
def mine_document_concepts(doc_id: str):
    """Mines Wiki concepts from an existing document."""
    import os
    from backend.database.crud import get_document_by_id, get_chunks_for_document
    from backend.knowledge.concept_miner import extract_concepts_from_text
    from backend.knowledge.relationship_builder import auto_build_cross_document_links

    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    text_to_mine = ""
    # Check extracted file first
    extracted_path = os.path.join("raw", "extracted", f"{doc_id}.txt")
    if os.path.exists(extracted_path):
        with open(extracted_path, "r", encoding="utf-8") as f:
            text_to_mine = f.read()

    if not text_to_mine:
        chunks = get_chunks_for_document(doc_id)
        text_to_mine = "\n\n".join([c.text_content for c in chunks])

    if not text_to_mine:
        raise HTTPException(status_code=422, detail="No text available for this document.")

    discovered = extract_concepts_from_text(text_to_mine, document_id=doc_id, page_number=1)
    auto_build_cross_document_links()

    return {
        "success": True,
        "document_id": doc_id,
        "concepts_mined": len(discovered),
        "discovered": discovered,
    }


@router.get("/{node_id}")
def get_concept_detail(node_id: str):
    """Retrieves concept node details, relationships, and anchored source references."""
    node = get_knowledge_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Knowledge node not found.")

    rels = get_node_relationships(node.id)
    sources = get_sources_for_node(node.id)

    return {
        "node": node,
        "relationships": rels,
        "sources": sources,
    }


@router.post("", response_model=KnowledgeNodeModel, status_code=status.HTTP_201_CREATED)
def create_concept(req: CreateConceptRequest):
    """Creates a new structured concept node in the Second Brain Wiki."""
    if not req.name.strip() or not req.summary.strip():
        raise HTTPException(status_code=400, detail="Name and summary cannot be empty.")
    node = upsert_knowledge_node(
        name=req.name,
        category=req.category,
        summary=req.summary,
        canonical_definition=req.canonical_definition,
    )
    return node


@router.get("/{node_id}/relationships", response_model=List[KnowledgeRelationshipModel])
def get_relationships(node_id: str):
    """Lists all incoming and outgoing connections for a given concept."""
    return get_node_relationships(node_id)


@router.post("/relationships", status_code=status.HTTP_201_CREATED)
def create_relationship(req: AddRelationshipRequest):
    """Creates a semantic link between two knowledge nodes."""
    success = add_knowledge_relationship(
        source_node_id=req.source_node_id,
        target_node_id=req.target_node_id,
        relation_type=req.relation_type,
        confidence=req.confidence,
        description=req.description,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to create relationship.")
    return {"created": True}
