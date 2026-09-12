from __future__ import annotations

"""
DocMind Second Brain — Output & Deliverables Engine
Generates structured study deliverables (Notes, Summaries, Quizzes, Flashcards)
and saves them to the output/ directory while indexing records in SQLite.
"""

import os
import time
import re
from typing import List, Dict, Any, Optional
from core.llm import generate, is_model_loaded
from core.embedder import embed_query
from core.vector_store import query as vector_query
from backend.database.crud import create_output_artifact
from backend.database.models import OutputArtifactModel


OUTPUT_SUBDIRS = {
    "STUDY_NOTES": os.path.join("output", "notes"),
    "SUMMARY": os.path.join("output", "summaries"),
    "REPORT": os.path.join("output", "reports"),
    "QUIZ": os.path.join("output", "quizzes"),
    "FLASHCARDS": os.path.join("output", "notes"),
}


def _ensure_output_dirs() -> None:
    """Ensures deliverable output directories exist."""
    for path in OUTPUT_SUBDIRS.values():
        os.makedirs(path, exist_ok=True)


def _sanitize_filename(name: str) -> str:
    """Creates safe filename string."""
    clean = re.sub(r"[^\w\s-]", "", name).strip().lower()
    return re.sub(r"[-\s]+", "_", clean)[:40]


def generate_study_deliverable(
    topic: str,
    output_type: str = "STUDY_NOTES",
    folder_scope: Optional[List[str]] = None,
    user_id: str = "default_user",
    max_tokens: int = 768,
) -> Dict[str, Any]:
    """
    Generates a structured study artifact based on indexed document evidence.
    Saves markdown to output/ and indexes in SQLite.
    """
    _ensure_output_dirs()

    # 1. Retrieve evidence from Vector DB
    query_emb = embed_query(f"{topic} concepts definitions examples")
    target_folders = None if (not folder_scope or "All" in folder_scope) else folder_scope
    search_res = vector_query(query_emb, top_k=4, folder=target_folders)

    chunks = search_res.get("chunks", [])
    metadatas = search_res.get("metadatas", [])

    if not chunks:
        return {
            "success": False,
            "error": "No matching document context found in the selected folder scope.",
        }

    # Format context
    context_blocks = []
    source_labels = []
    for i, chk in enumerate(chunks):
        meta = metadatas[i] if i < len(metadatas) else {}
        src = meta.get("source", "Document")
        pg = meta.get("page", 1)
        context_blocks.append(f"[Source: {src} | Page: {pg}]\n{chk.strip()}")
        label = f"{src} (p. {pg})"
        if label not in source_labels:
            source_labels.append(label)

    evidence_str = "\n\n---\n\n".join(context_blocks)

    # 2. Resolve Strategy via Factory (Strategy & Factory Pattern / OCP)
    from backend.output.strategies.factory import default_deliverable_factory
    strategy = default_deliverable_factory.get_strategy(output_type)
    canonical_type = strategy.deliverable_type

    instruction = strategy.build_instruction(topic)
    full_prompt = f"{instruction}\n\nStudy Material Context:\n{evidence_str}"

    # 3. Generate response using local LLM
    if not is_model_loaded():
        # Fallback offline synthesis if LLM is currently unconfigured
        generated_content = strategy.format_offline_content(
            topic=topic,
            chunks=chunks,
            source_labels=source_labels,
        )
    else:
        try:
            generated_content = generate(
                prompt=full_prompt,
                context="",
                max_tokens=max_tokens,
                temperature=0.2,
                stream=False,
            )
        except Exception as e:
            return {"success": False, "error": f"Generation failed: {str(e)}"}

    # 4. Save to Disk under output/
    sub_dir = os.path.join("output", strategy.default_subdir)

    filename = f"{_sanitize_filename(topic)}_{int(time.time())}.md"
    file_path = os.path.join(sub_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# DocMind Deliverable: {topic}\n")
        f.write(f"*Type: {output_type} | Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write(generated_content)
        f.write("\n\n---\n### Verified Source Citations\n")
        for s in source_labels:
            f.write(f"- {s}\n")

    # 5. Record Artifact in SQLite
    doc_ids = [m.get("document_id", "") for m in metadatas if m.get("document_id")]
    artifact = create_output_artifact(
        user_id=user_id,
        output_type=output_type,
        title=f"{topic} ({output_type})",
        file_path=file_path,
        content_preview=generated_content[:300],
        source_doc_ids=list(set(doc_ids)),
    )

    return {
        "success": True,
        "artifact_id": artifact.id,
        "file_path": file_path,
        "content": generated_content,
        "sources": source_labels,
    }
