from __future__ import annotations

"""
DocMind Second Brain — Context Assembler
Unifies Document Evidence, Wiki Knowledge Graph, and Selective Memory into a grounded ChatML prompt.
"""

import os
from typing import List, Dict, Any, Optional
from backend.memory.memory_manager import retrieve_relevant_memories
from backend.knowledge.graph_service import find_connected_concepts, format_wiki_context_for_prompt
from backend.orchestration.budget_controller import allocate_context_budget
from config import DOCMIND_SYSTEM_PROMPT

RULES_PATH = os.path.join("ctx", "rules", "anti_hallucination.md")


def _load_anti_hallucination_rules() -> str:
    """Loads grounding and citation rules from disk."""
    if os.path.exists(RULES_PATH):
        try:
            with open(RULES_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return (
        "CORE GROUNDING RULES:\n"
        "1. Answer strictly based on the provided document evidence.\n"
        "2. If the answer is absent from the documents, state: 'I couldn't find this information in the uploaded documents.'\n"
        "3. Always cite the document name and page number for factual claims."
    )


def assemble_grounded_context(
    query: str,
    raw_chunks: List[str],
    metadatas: List[Dict[str, Any]],
    user_id: str = "default_user",
    active_project: str = "DEFAULT",
    history: Optional[List[Dict[str, str]]] = None,
    include_wiki: bool = True,
    include_memory: bool = True,
) -> Dict[str, Any]:
    """
    Assembles a multi-layered context dictionary for the LLM.
    Returns:
      - 'context': The formatted text block to feed to core.llm.generate()
      - 'sources': List of formatted citation strings (e.g. 'Operating_Systems.pdf (p. 210)')
      - 'wiki_concepts': List of connected concept names
      - 'activated_memories': List of active memory values
    """
    # 1. Format Document Evidence Chunks
    formatted_chunks: List[str] = []
    sources: List[str] = []
    seen_snippets = set()

    for idx, chunk in enumerate(raw_chunks):
        clean_chk = chunk.strip()
        chunk_key = clean_chk[:120]
        if chunk_key in seen_snippets:
            continue
        seen_snippets.add(chunk_key)

        meta = metadatas[idx] if idx < len(metadatas) else {}
        src_name = meta.get("source") or meta.get("filename") or "Document"
        folder = meta.get("folder", "General")
        page = meta.get("page") or meta.get("page_number") or 1

        chunk_header = f"[Source: {src_name} | Page: {page} | Scope: {folder}]"
        formatted_chunks.append(f"{chunk_header}\n{clean_chk}")

        cite_label = f"{src_name} (p. {page})" if page else src_name
        if cite_label not in sources:
            sources.append(cite_label)

    # 2. Retrieve & Format Wiki Knowledge Connections
    connected_concepts = []
    wiki_context_str = ""
    if include_wiki:
        try:
            connected_concepts = find_connected_concepts(query=query, max_concepts=2)
            if connected_concepts:
                wiki_context_str = format_wiki_context_for_prompt(connected_concepts)
        except Exception:
            connected_concepts = []
            wiki_context_str = ""

    # 3. Retrieve & Format Selective Memories
    activated_memories = []
    mem_context_str = ""
    if include_memory:
        try:
            active_mems = retrieve_relevant_memories(
                user_id=user_id,
                query=query,
                active_project=active_project,
                top_k=2,
            )
            if active_mems:
                mem_lines = ["ACTIVE USER PREFERENCES & CONTEXT:"]
                for m in active_mems:
                    mem_lines.append(f"- [{m.category}] {m.memory_value}")
                    activated_memories.append(m.memory_value)
                mem_context_str = "\n".join(mem_lines)
        except Exception:
            activated_memories = []
            mem_context_str = ""

    # 4. Token Budgeting Check
    budget = allocate_context_budget(
        evidence_chunks=formatted_chunks,
        wiki_context=wiki_context_str,
        memory_context=mem_context_str,
        history_turns=history or [],
    )

    # 5. Build Unified Grounded Context Block
    context_sections = []

    # A. Active User Preferences
    if budget["budgeted_memory"]:
        context_sections.append(budget["budgeted_memory"])

    # B. Primary Document Evidence
    if budget["budgeted_chunks"]:
        docs_header = "PRIMARY DOCUMENT EVIDENCE (Source of Truth):"
        docs_body = "\n\n---\n\n".join(budget["budgeted_chunks"])
        context_sections.append(f"{docs_header}\n{docs_body}")

    # C. Structured Wiki Knowledge Graph
    if budget["budgeted_wiki"]:
        context_sections.append(budget["budgeted_wiki"])

    # D. Grounding directives
    anti_hallucination = _load_anti_hallucination_rules()
    if anti_hallucination:
        context_sections.append(f"GROUNDING INSTRUCTIONS:\n{anti_hallucination}")

    full_context = "\n\n====================\n\n".join(context_sections)

    wiki_names = [c["name"] for c in connected_concepts]

    return {
        "context": full_context,
        "sources": sources,
        "wiki_concepts": wiki_names,
        "activated_memories": activated_memories,
        "budget_info": budget,
    }
