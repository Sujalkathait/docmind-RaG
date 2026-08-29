from __future__ import annotations

import os
import json
import time
import uuid
import re
from typing import Any, Optional, Union, List, Dict
from dataclasses import dataclass, asdict, field

CHAT_DIR = os.getenv("CHAT_HISTORY_DIR", "chat_history")


def _clean_session_title(raw_text: str) -> str:
    """Extracts a clean, human-readable session title without raw markdown code fences."""
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    for line in lines:
        # Strip markdown codeblocks, headers, bullets, and backticks
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*", "", line).strip()
        cleaned = re.sub(r"^[#*`>\-\s\d\.]+", "", cleaned).strip()
        cleaned = re.sub(r"[`*#_]", "", cleaned).strip()
        if len(cleaned) >= 3:
            return cleaned[:36]
    return "Chat Session"


def _ensure_chat_dir():
    """Ensures the chat history directory exists on disk."""
    os.makedirs(CHAT_DIR, exist_ok=True)


def _get_session_file_path(session_id: str) -> str:
    """Returns the sanitized file path for a session JSON file."""
    _ensure_chat_dir()
    clean_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
    return os.path.join(CHAT_DIR, f"{clean_id}.json")


# ===========================
# Core Models & Data Structures
# ===========================


@dataclass
class ChatMessage:
    id: str
    role: str  # "user" | "assistant"
    content: str
    timestamp: float
    sources: list[str] = field(default_factory=list)
    execution_time: float | None = None
    tokens_per_sec: float | None = None
    retrieval_time: float | None = None
    folder_scope: Any = "All"
    feedback: str | None = None  # "liked" | "disliked" | None
    mode: str | None = None  # "llm" | "direct" | None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ChatMessage:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", time.time()),
            sources=data.get("sources", []),
            execution_time=data.get("execution_time") or data.get("time"),
            tokens_per_sec=data.get("tokens_per_sec"),
            retrieval_time=data.get("retrieval_time"),
            folder_scope=data.get("folder_scope", "All"),
            feedback=data.get("feedback"),
            mode=data.get("mode"),
        )


@dataclass
class ChatSession:
    id: str
    title: str
    created_at: float
    updated_at: float
    is_pinned: bool = False
    folder_scope: Any = "All"
    messages: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ChatSession:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", "New Chat"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            is_pinned=bool(data.get("is_pinned", False)),
            folder_scope=data.get("folder_scope", "All"),
            messages=data.get("messages", []),
        )


# ===========================
# Persistence API
# ===========================


def create_session(
    title: str = "New Chat",
    folder_scope: Any = "All",
) -> dict:
    """
    Creates a new chat session and saves it to disk.
    Returns the session dictionary.
    """
    _ensure_chat_dir()
    now = time.time()
    session_id = f"chat_{int(now)}_{uuid.uuid4().hex[:6]}"
    session = ChatSession(
        id=session_id,
        title=title.strip() if title else "New Chat",
        created_at=now,
        updated_at=now,
        is_pinned=False,
        folder_scope=folder_scope,
        messages=[],
    )

    save_session(session.to_dict())
    return session.to_dict()


def save_session(session_dict: dict) -> bool:
    """Saves a session dictionary to disk atomically."""
    _ensure_chat_dir()
    session_id = session_dict.get("id")
    if not session_id:
        return False

    session_dict["updated_at"] = time.time()
    file_path = _get_session_file_path(session_id)
    temp_path = f"{file_path}.tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(session_dict, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, file_path)
        return True
    except Exception as e:
        print(f"Error saving chat session '{session_id}': {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False


def get_session(session_id: str) -> dict | None:
    """Loads a single session by ID from disk."""
    if not session_id:
        return None

    file_path = _get_session_file_path(session_id)
    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Error reading chat session '{session_id}': {e}")
        return None


def get_all_sessions() -> list[dict]:
    """
    Returns all saved chat sessions ordered:
    Pinned first (by updated_at desc), then non-pinned (by updated_at desc).
    """
    _ensure_chat_dir()
    sessions = []

    for filename in os.listdir(CHAT_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(CHAT_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "id" in data:
                        sessions.append(data)
            except Exception as e:
                print(f"Error parsing session file '{filename}': {e}")

    # Sort: Pinned first (True > False), then newest updated_at
    sessions.sort(
        key=lambda s: (not s.get("is_pinned", False), -s.get("updated_at", 0))
    )
    return sessions


def add_message(
    session_id: str,
    role: str,
    content: str,
    sources: list[str] | None = None,
    execution_time: float | None = None,
    folder_scope: Any = "All",
    feedback: str | None = None,
    mode: str | None = None,
    tokens_per_sec: float | None = None,
    retrieval_time: float | None = None,
) -> dict | None:
    """
    Appends a message to the specified session, auto-generating title if first user message.
    """
    session = get_session(session_id)
    if not session:
        session = create_session(folder_scope=folder_scope)
        session_id = session["id"]

    msg = ChatMessage(
        id=str(uuid.uuid4()),
        role=role,
        content=content,
        timestamp=time.time(),
        sources=sources or [],
        execution_time=execution_time,
        tokens_per_sec=tokens_per_sec,
        retrieval_time=retrieval_time,
        folder_scope=folder_scope,
        feedback=feedback,
        mode=mode,
    )

    session["messages"].append(msg.to_dict())

    # Auto-title on first user message if title is default
    if (
        role == "user"
        and session.get("title", "New Chat") in ("New Chat", "Untitled Chat")
        and content.strip()
    ):
        session["title"] = _clean_session_title(content)

    session["updated_at"] = time.time()
    save_session(session)
    return msg.to_dict()


def set_message_feedback(
    session_id: str,
    message_id: str,
    feedback: str | None,
) -> bool:
    """Updates the feedback (like/dislike) for a specific message in a session."""
    session = get_session(session_id)
    if not session:
        return False

    updated = False
    for msg in session.get("messages", []):
        if msg.get("id") == message_id:
            msg["feedback"] = feedback
            updated = True
            break

    if updated:
        session["updated_at"] = time.time()
        return save_session(session)
    return False


def rename_session(session_id: str, new_title: str) -> bool:
    """Renames an existing chat session."""
    session = get_session(session_id)
    if not session:
        return False

    clean_title = new_title.strip() if new_title.strip() else "Untitled Chat"
    session["title"] = clean_title
    session["updated_at"] = time.time()
    return save_session(session)


def toggle_pin_session(session_id: str) -> bool:
    """Toggles the pinned status of a session."""
    session = get_session(session_id)
    if not session:
        return False

    session["is_pinned"] = not session.get("is_pinned", False)
    session["updated_at"] = time.time()
    return save_session(session)


def delete_session(session_id: str) -> bool:
    """Deletes a chat session file from disk."""
    file_path = _get_session_file_path(session_id)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting session '{session_id}': {e}")
            return False
    return False


def clear_all_sessions() -> bool:
    """Deletes all saved chat sessions."""
    _ensure_chat_dir()
    success = True
    for filename in os.listdir(CHAT_DIR):
        if filename.endswith(".json"):
            try:
                os.remove(os.path.join(CHAT_DIR, filename))
            except Exception:
                success = False
    return success


def get_latest_or_default_session() -> dict:
    """
    Returns the most recent active session, or creates a new one if none exist.
    """
    sessions = get_all_sessions()
    if sessions:
        return sessions[0]
    return create_session()
