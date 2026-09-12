from __future__ import annotations

"""
DocMind Second Brain — Chat Service (Service Layer / DIP / SRP)
Encapsulates chat execution, retrieval orchestration, prompt building, and session management.
Separates application logic from FastAPI transport/routing controllers.
"""

from typing import List, Dict, Any, Optional, Generator, Tuple
import json

from backend.repositories.session_repository import BaseSessionRepository, default_session_repository
from backend.orchestration.context_assembler import assemble_grounded_context
from backend.orchestration.prompt_builder import ChatMLPromptBuilder
from backend.memory.memory_evaluator import evaluate_interaction_for_memory
from core.embedder import embed_query
from core.vector_store import query as vector_query
from core.llm import generate, is_model_loaded, get_dynamic_max_tokens, _clean_output_text
from config import TOP_K, DOCMIND_SYSTEM_PROMPT


class ChatService:
    """
    Core Domain Service for DocMind Chat Interactions.
    Accepts an injected BaseSessionRepository instance adhering to DIP.
    """

    def __init__(self, session_repo: Optional[BaseSessionRepository] = None):
        self.session_repo = session_repo or default_session_repository

    def list_sessions(self) -> List[Dict[str, Any]]:
        return self.session_repo.list_sessions()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.session_repo.get_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        return self.session_repo.delete_session(session_id)

    def prepare_chat(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        folder_scope: Optional[List[str]] = None,
        user_id: str = "default_user",
    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, str]]]:
        """
        Orchestrates session creation, retrieval, and grounded context assembly.
        Returns (session, assembled_context, history_turns).
        """
        session = self.session_repo.get_session(session_id) if session_id else None
        if not session:
            session = self.session_repo.create_session(
                title=prompt[:32],
                folder_scope=folder_scope or ["All"],
            )
            session_id = session["id"]

        # Append user turn to repository
        user_msg = {
            "id": f"msg_{len(session.get('messages', [])) + 1}",
            "role": "user",
            "content": prompt,
            "folder_scope": folder_scope or "All",
        }
        session.setdefault("messages", []).append(user_msg)
        self.session_repo.save_session(session)

        # Retrieval
        query_emb = embed_query(prompt)
        effective_folders = None if (not folder_scope or "All" in folder_scope) else folder_scope
        search_res = vector_query(query_emb, top_k=TOP_K, folder=effective_folders)
        chunks = search_res.get("chunks", [])
        metadatas = search_res.get("metadatas", [])

        history_turns = session.get("messages", [])[-5:-1]

        assembled = assemble_grounded_context(
            query=prompt,
            raw_chunks=chunks,
            metadatas=metadatas,
            user_id=user_id,
            history=history_turns,
        )

        return session, assembled, history_turns

    def stream_chat_generator(
        self,
        prompt: str,
        session_id: str,
        assembled: Dict[str, Any],
        history_turns: List[Dict[str, str]],
        folder_scope: Optional[List[str]] = None,
        user_id: str = "default_user",
    ) -> Generator[str, None, None]:
        """Generator yielding SSE chunks for client response."""
        full_text: List[str] = []
        max_tokens = get_dynamic_max_tokens(prompt)

        metadata_payload = {
            "conversation_id": session_id,
            "sources": assembled["sources"],
            "wiki_concepts": assembled["wiki_concepts"],
            "activated_memories": assembled["activated_memories"],
        }

        try:
            tok_gen = generate(
                prompt=prompt,
                context=assembled["context"],
                history=history_turns,
                max_tokens=max_tokens,
                stream=True,
            )
            for tok in tok_gen:
                full_text.append(tok)
                chunk_data = json.dumps({"delta": tok})
                yield f"data: {chunk_data}\n\n"

            complete_answer = _clean_output_text("".join(full_text))
            if not complete_answer.strip():
                complete_answer = "I couldn't find this information in the uploaded documents."

            # Save assistant message to session repository
            session = self.session_repo.get_session(session_id)
            if session:
                assistant_msg = {
                    "id": f"msg_{len(session.get('messages', [])) + 1}",
                    "role": "assistant",
                    "content": complete_answer,
                    "sources": assembled["sources"],
                    "folder_scope": folder_scope or "All",
                    "mode": "llm",
                }
                session.setdefault("messages", []).append(assistant_msg)
                self.session_repo.save_session(session)

            # Auto-extract memories in background
            evaluate_interaction_for_memory(prompt, complete_answer, user_id=user_id)

            yield f"data: {json.dumps({'done': True, 'metadata': metadata_payload})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            err_msg = f"\n\n[DocMind LLM Notice]: {str(e)}"
            yield f"data: {json.dumps({'delta': err_msg})}\n\n"
            yield "data: [DONE]\n\n"


# Singleton instance for dependency injection
default_chat_service = ChatService()
