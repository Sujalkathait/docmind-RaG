from __future__ import annotations

"""
DocMind Second Brain — Session Repository (Repository Pattern / SRP)
Abstracts session persistence and retrieval from business and routing logic.
Adheres to Single Responsibility Principle (SRP) and Dependency Inversion (DIP).
"""

import os
import json
import time
import uuid
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
try:
    from config import CHAT_DIR
except ImportError:
    CHAT_DIR = os.getenv("CHAT_HISTORY_DIR", os.path.join("ctx", "sessions"))


class BaseSessionRepository(ABC):
    """Abstract interface for chat session persistence."""

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves session by ID."""
        pass

    @abstractmethod
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lists all active sessions ordered by pinned status and recency."""
        pass

    @abstractmethod
    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """Persists a session."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Deletes a session."""
        pass

    @abstractmethod
    def create_session(self, title: str = "New Chat", folder_scope: Any = "All") -> Dict[str, Any]:
        """Creates and stores a fresh session."""
        pass


class FileSessionRepository(BaseSessionRepository):
    """
    Concrete filesystem implementation of SessionRepository.
    Stores atomic JSON session files in the configured chat directory.
    """

    def __init__(self, storage_dir: str = CHAT_DIR):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_file_path(self, session_id: str) -> str:
        clean_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.storage_dir, f"{clean_id}.json")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        file_path = self._get_file_path(session_id)
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = []
        if not os.path.exists(self.storage_dir):
            return []

        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.storage_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "id" in data:
                            sessions.append(data)
                except Exception:
                    continue

        # Pinned first, then newest updated_at
        sessions.sort(key=lambda s: (not s.get("is_pinned", False), -s.get("updated_at", 0)))
        return sessions

    def save_session(self, session_data: Dict[str, Any]) -> bool:
        session_id = session_data.get("id")
        if not session_id:
            return False
        file_path = self._get_file_path(session_id)
        try:
            temp_path = f"{file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, file_path)
            return True
        except Exception:
            return False

    def delete_session(self, session_id: str) -> bool:
        file_path = self._get_file_path(session_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception:
                return False
        return False

    def create_session(self, title: str = "New Chat", folder_scope: Any = "All") -> Dict[str, Any]:
        now = time.time()
        session_id = f"session_{int(now)}_{uuid.uuid4().hex[:6]}"
        session = {
            "id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "is_pinned": False,
            "folder_scope": folder_scope,
            "messages": [],
        }
        self.save_session(session)
        return session


# Default singleton instance for dependency injection
default_session_repository = FileSessionRepository()
