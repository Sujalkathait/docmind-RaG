from __future__ import annotations

"""
DocMind Second Brain — Chat REST API Router
Handles conversational queries with grounded context, citation tracking, SSE streaming,
and robust error handling with zero external API keys.
"""

import json
import time
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.embedder import embed_query
from core.vector_store import query as vector_query
from core.llm import generate, is_model_loaded, get_dynamic_max_tokens, get_model_info
from core.chat_manager import (
    get_all_sessions,
    get_session,
    add_message,
    create_session,
)
from backend.orchestration.context_assembler import assemble_grounded_context
from backend.memory.memory_evaluator import evaluate_interaction_for_memory
from backend.repositories.session_repository import default_session_repository
from config import TOP_K

router = APIRouter(prefix="", tags=["Chat"])


class ChatMessageRequest(BaseModel):
    # Support both naming conventions seamlessly
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    message: Optional[str] = None
    query: Optional[str] = None
    folder_scope: Optional[Union[List[str], str]] = None
    folder: Optional[str] = None
    user_id: str = "default_user"
    stream: bool = True

    def get_effective_message(self) -> str:
        msg = self.message or self.query or ""
        return msg.strip()

    def get_effective_conv_id(self) -> Optional[str]:
        return self.conversation_id or self.session_id

    def get_effective_folders(self) -> Optional[List[str]]:
        raw = self.folder_scope or self.folder
        if not raw or raw == "All" or raw == "All Collections":
            return None
        if isinstance(raw, str):
            return [raw]
        return raw


@router.post("/chat")
@router.post("/chat/")
def chat_endpoint(req: ChatMessageRequest):
    """
    Submits user query to DocMind Second Brain.
    Retrieves ground-truth evidence + wiki concepts + active memory.
    Streams back tokens using Server-Sent Events (SSE) or returns JSON.
    """
    prompt = req.get_effective_message()
    if not prompt:
        raise HTTPException(status_code=400, detail="Message/query cannot be empty.")

    # 1. Resolve or create session
    conv_id = req.get_effective_conv_id()
    session = get_session(conv_id) if conv_id else None
    effective_folders = req.get_effective_folders()

    if not session:
        session = create_session(folder_scope=effective_folders or ["All"])
        conv_id = session["id"]

    # 2. Record user turn
    add_message(
        session_id=conv_id,
        role="user",
        content=prompt,
        folder_scope=effective_folders or "All",
    )

    # 3. Vector & Unified Retrieval
    query_emb = embed_query(prompt)
    search_res = vector_query(query_emb, top_k=TOP_K, folder=effective_folders)
    chunks = search_res.get("chunks", [])
    metadatas = search_res.get("metadatas", [])

    history_turns = session.get("messages", [])[-4:]

    assembled = assemble_grounded_context(
        query=prompt,
        raw_chunks=chunks,
        metadatas=metadatas,
        user_id=req.user_id,
        history=history_turns,
    )

    # 4. Generate Answer via Local LLM
    max_tokens = get_dynamic_max_tokens(prompt)

    metadata_payload = {
        "conversation_id": conv_id,
        "sources": assembled["sources"],
        "retrieved_chunks": len(chunks),
        "wiki_concepts": assembled["wiki_concepts"],
        "injected_concepts": len(assembled["wiki_concepts"]),
        "activated_memories": assembled["activated_memories"],
        "injected_memories": len(assembled["activated_memories"]),
    }

    if req.stream:
        def event_streamer():
            full_text = []
            try:
                generator = generate(
                    prompt=prompt,
                    context=assembled["context"],
                    history=history_turns,
                    max_tokens=max_tokens,
                    stream=True,
                )
                for tok in generator:
                    full_text.append(tok)
                    # Yield SSE payload
                    chunk_data = json.dumps({"delta": tok})
                    yield f"data: {chunk_data}\n\n"

                complete_answer = "".join(full_text)
                if not complete_answer.strip():
                    complete_answer = "I searched your documents but found no conclusive evidence to answer this question."

                # Save assistant response
                add_message(
                    session_id=conv_id,
                    role="assistant",
                    content=complete_answer,
                    sources=assembled["sources"],
                    folder_scope=effective_folders or "All",
                    mode="llm",
                )

                # Post-response selective memory update
                evaluate_interaction_for_memory(prompt, complete_answer, user_id=req.user_id)

                # Send final metadata and DONE token
                yield f"data: {json.dumps({'done': True, 'metadata': metadata_payload})}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                err_msg = f"\n\n[DocMind LLM Notice]: {str(e)}"
                yield f"data: {json.dumps({'delta': err_msg})}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_streamer(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        try:
            ans_text = generate(
                prompt=prompt,
                context=assembled["context"],
                history=history_turns,
                max_tokens=max_tokens,
                stream=False,
            )
        except Exception as e:
            ans_text = f"[DocMind LLM Notice]: Unable to generate response with local model: {str(e)}"

        add_message(
            session_id=conv_id,
            role="assistant",
            content=ans_text,
            sources=assembled["sources"],
            folder_scope=effective_folders or "All",
            mode="llm",
        )

        mem_update = evaluate_interaction_for_memory(prompt, ans_text, user_id=req.user_id)

        return {
            "conversation_id": conv_id,
            "answer": ans_text,
            "sources": assembled["sources"],
            "wiki_concepts": assembled["wiki_concepts"],
            "activated_memories": assembled["activated_memories"],
            "memory_update": mem_update,
            "metadata": metadata_payload,
        }

# Session & Conversation endpoints with aliases
@router.get("/conversations")
@router.get("/chat/sessions")
def list_conversations():
    """Returns all saved chat conversation summaries."""
    sessions = default_session_repository.list_sessions()
    return {"sessions": sessions} if isinstance(sessions, list) else sessions


@router.get("/conversations/{conv_id}")
@router.get("/chat/history/{conv_id}")
def get_conversation_history(conv_id: str):
    """Returns full messages for a conversation session."""
    session = default_session_repository.get_session(conv_id)
    if not session:
        return []
    return session.get("messages", [])


@router.delete("/conversations/{conv_id}")
@router.delete("/chat/sessions/{conv_id}")
def delete_conversation(conv_id: str):
    """Deletes a chat conversation session from disk."""
    success = default_session_repository.delete_session(conv_id)
    if not success:
        from core.chat_manager import delete_session as cm_delete_session
        if not cm_delete_session(conv_id):
            raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found.")
    return {
        "deleted": True,
        "success": True,
        "session_id": conv_id,
        "message": f"Conversation '{conv_id}' deleted successfully.",
    }


@router.delete("/conversations")
@router.delete("/chat/sessions")
def clear_all_conversations():
    """Clears all chat conversations."""
    from core.chat_manager import clear_all_sessions
    cleared = clear_all_sessions()
    return {
        "deleted_all": cleared,
        "message": "All conversations have been cleared.",
    }

