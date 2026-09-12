from __future__ import annotations

"""
DocMind Second Brain — Wiki Knowledge Graph Service
Traverses relationships, extracts connected concept subgraphs, and formats graph context for LLM prompt injection.
"""

from typing import List, Dict, Any, Optional
from backend.database.crud import (
    list_knowledge_nodes,
    get_knowledge_node,
    get_node_relationships,
    get_sources_for_node,
)
from backend.database.models import KnowledgeNodeModel, KnowledgeRelationshipModel


def find_connected_concepts(query: str, max_concepts: int = 3) -> List[Dict[str, Any]]:
    """
    Given a query, identifies relevant concepts in the Wiki and traverses 1-hop edges.
    Returns structured list of concept summaries with cross-references.
    """
    all_nodes = list_knowledge_nodes()
    q_lower = query.lower()

    # Find matching nodes
    matched_nodes: List[KnowledgeNodeModel] = []
    for node in all_nodes:
        if node.name.lower() in q_lower or any(word in q_lower for word in node.name.lower().split() if len(word) > 3):
            matched_nodes.append(node)
        elif q_lower in node.summary.lower():
            matched_nodes.append(node)

    results = []
    seen_nodes = set()

    for node in matched_nodes[:max_concepts]:
        if node.id in seen_nodes:
            continue
        seen_nodes.add(node.id)

        # Get connections (outgoing and incoming)
        relationships = get_node_relationships(node.id)
        sources = get_sources_for_node(node.id)

        doc_refs = []
        for s in sources:
            ref = f"{s.document_name or 'Doc'} (p. {s.page_number})"
            if ref not in doc_refs:
                doc_refs.append(ref)

        connected_terms = []
        for rel in relationships:
            other = rel.target_name if rel.source_node_id == node.id else rel.source_name
            if other and other not in connected_terms:
                connected_terms.append(f"{other} ({rel.relation_type})")

        results.append({
            "id": node.id,
            "name": node.name,
            "category": node.category,
            "canonical_definition": node.canonical_definition or node.summary,
            "connected_concepts": connected_terms,
            "source_references": doc_refs,
        })

    return results


def format_wiki_context_for_prompt(connected_concepts: List[Dict[str, Any]]) -> str:
    """
    Formats extracted Wiki knowledge and relationships into clean, high-density lines for LLM context.
    """
    if not connected_concepts:
        return ""

    lines = ["Connected Knowledge Graph (Wiki):"]
    for c in connected_concepts:
        def_line = f"• Concept: {c['name']} [{c['category']}]"
        if c.get("canonical_definition"):
            def_line += f" — {c['canonical_definition']}"
        lines.append(def_line)

        if c.get("connected_concepts"):
            links_str = ", ".join(c["connected_concepts"][:3])
            lines.append(f"  ↳ Relationships: {links_str}")

        if c.get("source_references"):
            src_str = ", ".join(c["source_references"][:2])
            lines.append(f"  ↳ Grounded Sources: {src_str}")

    return "\n".join(lines)


def get_full_graph_for_ui() -> Dict[str, Any]:
    """Returns nodes and edges serialized for graph rendering or dashboard display."""
    nodes = list_knowledge_nodes()
    all_edges: List[Dict[str, Any]] = []
    seen_edges = set()

    for n in nodes:
        rels = get_node_relationships(n.id)
        for r in rels:
            edge_key = tuple(sorted([r.source_node_id, r.target_node_id])) + (r.relation_type,)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                all_edges.append({
                    "id": r.id,
                    "source": r.source_name or r.source_node_id,
                    "target": r.target_name or r.target_node_id,
                    "relation_type": r.relation_type,
                    "description": r.description or "",
                    "confidence": r.confidence,
                })

    return {
        "nodes": [
            {
                "id": n.id,
                "name": n.name,
                "category": n.category,
                "summary": n.summary,
                "definition": n.canonical_definition,
            }
            for n in nodes
        ],
        "edges": all_edges,
        "total_nodes": len(nodes),
        "total_edges": len(all_edges),
    }
