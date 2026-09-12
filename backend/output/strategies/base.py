from __future__ import annotations

"""
DocMind Second Brain — Deliverable Strategy Interface (Strategy Pattern / OCP)
Defines the contract for all deliverable generation strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class DeliverableStrategy(ABC):
    """
    Abstract Strategy for generating educational deliverables (Notes, Summaries, Quizzes, etc.).
    Follows Strategy Pattern (Behavioral) and Open/Closed Principle (SOLID).
    """

    @property
    @abstractmethod
    def deliverable_type(self) -> str:
        """Returns the canonical upper-case deliverable identifier (e.g. 'STUDY_NOTES')."""
        pass

    @property
    @abstractmethod
    def default_subdir(self) -> str:
        """Returns the relative subdirectory under output/ for this artifact."""
        pass

    @abstractmethod
    def build_instruction(self, topic: str) -> str:
        """Builds the instruction prompt tailored for this deliverable type."""
        pass

    @abstractmethod
    def format_offline_content(
        self,
        topic: str,
        chunks: List[str],
        source_labels: List[str],
    ) -> str:
        """
        Produces high-yield offline fallback content if local LLM is temporarily offline.
        Ensures system resilience (Graceful Degradation).
        """
        pass
