from __future__ import annotations

"""
DocMind Second Brain — Relationship Builder
Discovers inter-concept and cross-document links across the Wiki graph (e.g. OS Deadlock <-> DBMS Deadlock).
"""

from typing import List, Dict, Tuple
from backend.database.crud import (
    list_knowledge_nodes,
    add_knowledge_relationship,
    get_node_relationships,
    get_sources_for_node,
)

# Known semantic bridges across CS domains
DOMAIN_BRIDGES = [
    # (Node A, Node B, Relation Type, Confidence, Description)
    (
        "Deadlock",
        "Two-Phase Locking",
        "CAUSED_BY",
        0.95,
        "In DBMS, strict two-phase locking can induce cyclic wait conditions leading to transaction deadlocks.",
    ),
    (
        "Deadlock",
        "Semaphore",
        "RELATES_TO",
        0.90,
        "Improper acquisition order of binary semaphores or mutexes in operating systems directly causes circular wait deadlocks.",
    ),
    (
        "Two-Phase Locking",
        "ACID Properties",
        "IMPLEMENTS",
        0.98,
        "Two-Phase Locking enforces serializability, which guarantees the Isolation property of ACID.",
    ),
    (
        "Process Scheduling",
        "Semaphore",
        "COORDINATES_WITH",
        0.85,
        "Operating system schedulers coordinate with semaphores to transition threads between ready, running, and waiting states.",
    ),
    (
        "Virtual Memory",
        "Index / B-Tree",
        "SHARES_PRIMITIVE",
        0.80,
        "Both virtual memory paging and database B-Tree node management optimize for page-sized block I/O from storage.",
    ),
]


def auto_build_cross_document_links() -> int:
    """
    Scans existing Wiki knowledge nodes, identifies semantic connections,
    and commits cross-document relationship edges into SQLite.
    Returns the count of relationships established.
    """
    nodes = list_knowledge_nodes()
    node_map = {n.name.lower(): n for n in nodes}
    links_created = 0

    # 1. Apply domain bridge rules
    for name_a, name_b, rel_type, conf, desc in DOMAIN_BRIDGES:
        na = node_map.get(name_a.lower())
        nb = node_map.get(name_b.lower())
        if na and nb:
            # Check if they originate from different documents (cross-document link)
            sources_a = get_sources_for_node(na.id)
            sources_b = get_sources_for_node(nb.id)
            doc_ids_a = {s.document_id for s in sources_a}
            doc_ids_b = {s.document_id for s in sources_b}
            
            is_cross_doc = bool(doc_ids_a and doc_ids_b and (doc_ids_a != doc_ids_b))
            edge_desc = desc + (" [Cross-Document Connection]" if is_cross_doc else "")

            if add_knowledge_relationship(
                source_node_id=na.id,
                target_node_id=nb.id,
                relation_type=rel_type,
                confidence=conf,
                description=edge_desc,
            ):
                links_created += 1

    return links_created
