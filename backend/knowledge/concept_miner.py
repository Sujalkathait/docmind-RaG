from __future__ import annotations

"""
DocMind Second Brain — Wiki Concept Miner
Extracts structured concepts, definitions, entities, and grounding references from ingested document text.
"""

import re
from typing import List, Dict, Any, Optional
from backend.database.crud import (
    upsert_knowledge_node,
    link_knowledge_source,
    add_knowledge_relationship,
    get_knowledge_node,
    list_knowledge_nodes,
)
from backend.database.models import KnowledgeNodeModel

# Common foundational CS entities and concept patterns
CS_CORE_CONCEPTS = {
    "Deadlock": {
        "category": "CONCEPT",
        "keywords": ["deadlock", "coffman", "circular wait", "mutual exclusion", "hold and wait", "resource allocation graph"],
        "default_def": "A state where each member of a set of processes or transactions waits indefinitely for another to release a resource or lock.",
    },
    "Two-Phase Locking": {
        "category": "CONCEPT",
        "keywords": ["2pl", "two-phase locking", "growing phase", "shrinking phase", "strict 2pl"],
        "default_def": "A concurrency control protocol ensuring serializability by acquiring all locks before releasing any.",
    },
    "Semaphore": {
        "category": "CONCEPT",
        "keywords": ["semaphore", "wait()", "signal()", "counting semaphore", "binary semaphore", "mutex"],
        "default_def": "A synchronization tool consisting of an integer variable accessed only through wait() and signal() atomic operations.",
    },
    "Virtual Memory": {
        "category": "CONCEPT",
        "keywords": ["virtual memory", "paging", "page fault", "page table", "tlb", "segmentation"],
        "default_def": "A memory management capability of an OS that uses hardware and software to compensate for physical memory shortages.",
    },
    "TCP/IP": {
        "category": "TOPIC",
        "keywords": ["tcp", "tcp/ip", "three-way handshake", "syn", "ack", "flow control", "congestion control"],
        "default_def": "A suite of communication protocols used to interconnect network devices on the Internet.",
    },
    "ACID Properties": {
        "category": "CONCEPT",
        "keywords": ["acid", "atomicity", "consistency", "isolation", "durability", "transaction"],
        "default_def": "The set of properties (Atomicity, Consistency, Isolation, Durability) that guarantee database transactions are processed reliably.",
    },
    "Index / B-Tree": {
        "category": "CONCEPT",
        "keywords": ["b-tree", "b+ tree", "indexing", "clustered index", "secondary index"],
        "default_def": "A self-balancing tree data structure that maintains sorted data and allows searches, sequential access, insertions, and deletions in logarithmic time.",
    },
    "Process Scheduling": {
        "category": "TOPIC",
        "keywords": ["cpu scheduling", "round robin", "sjf", "fcfs", "priority scheduling", "context switch"],
        "default_def": "The OS mechanism that determines which process in the ready queue is allocated the CPU.",
    }
}

# Regex patterns that indicate formal definitions in textbook text
DEFINITION_PATTERNS = [
    r"(?i)\b([A-Z][A-Za-z0-9_\s]{2,30})\s+(?:is defined as|refers to|is a mechanism that|is a condition where|is a state where)\s+([^.\n]{15,250})\.",
    r"(?i)\b(?:Definition|Concept)\s*:\s*([A-Za-z0-9_\s]{2,30})[:\s]+([^.\n]{15,250})\.",
]


def extract_concepts_from_text(
    text: str,
    document_id: str,
    page_number: int = 1,
) -> List[Dict[str, Any]]:
    """
    Analyzes document text to extract technical concepts, definitions,
    and upserts them into the Second Brain Wiki graph.
    """
    discovered = []
    text_lower = text.lower()

    # 1. Match known CS foundational concepts
    for concept_name, info in CS_CORE_CONCEPTS.items():
        matches = [kw for kw in info["keywords"] if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)]
        if len(matches) >= 1:
            # Extract a representative sentence containing the concept
            snippet = ""
            for sentence in text.split("."):
                if any(m in sentence.lower() for m in matches):
                    snippet = sentence.strip() + "."
                    break
            if not snippet:
                snippet = text[:200]

            node = upsert_knowledge_node(
                name=concept_name,
                category=info["category"],
                summary=f"Key concept discussed in document context: {snippet[:140]}",
                canonical_definition=info["default_def"],
            )

            # Link source attribution
            link_knowledge_source(
                node_id=node.id,
                document_id=document_id,
                page_number=page_number,
                snippet=snippet,
            )

            discovered.append({
                "concept": concept_name,
                "category": info["category"],
                "node_id": node.id,
                "page": page_number,
                "snippet": snippet,
            })

    # 2. Match regex definition patterns
    for pat in DEFINITION_PATTERNS:
        for match in re.finditer(pat, text):
            term = match.group(1).strip()
            definition = match.group(2).strip()
            if 3 <= len(term) <= 35 and len(definition) >= 20:
                clean_term = " ".join(term.split())
                node = upsert_knowledge_node(
                    name=clean_term,
                    category="DEFINITION",
                    summary=f"{clean_term}: {definition}",
                    canonical_definition=definition,
                )
                link_knowledge_source(
                    node_id=node.id,
                    document_id=document_id,
                    page_number=page_number,
                    snippet=match.group(0),
                )
                discovered.append({
                    "concept": clean_term,
                    "category": "DEFINITION",
                    "node_id": node.id,
                    "page": page_number,
                    "snippet": definition,
                })

    return discovered
