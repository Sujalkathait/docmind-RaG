from __future__ import annotations

"""
DocMind Second Brain — Deliverable Factory (Factory Pattern / OCP / DIP)
Maintains a registry of DeliverableStrategy implementations, resolving strategy by key.
"""

from typing import Dict, Optional
from backend.output.strategies.base import DeliverableStrategy
from backend.output.strategies.study_notes import StudyNotesStrategy
from backend.output.strategies.summary import SummaryStrategy
from backend.output.strategies.quiz import QuizStrategy
from backend.output.strategies.flashcards import FlashcardsStrategy


class DeliverableFactory:
    """
    Factory & Registry for Deliverable Strategies.
    Complies with Open/Closed Principle: new strategies can be registered at runtime.
    """

    def __init__(self):
        self._strategies: Dict[str, DeliverableStrategy] = {}
        # Register standard default strategies
        self.register_strategy(StudyNotesStrategy())
        self.register_strategy(SummaryStrategy())
        self.register_strategy(QuizStrategy())
        self.register_strategy(FlashcardsStrategy())

    def register_strategy(self, strategy: DeliverableStrategy) -> None:
        """Registers a strategy under its canonical deliverable_type."""
        self._strategies[strategy.deliverable_type.upper()] = strategy

    def get_strategy(self, deliverable_type: str) -> DeliverableStrategy:
        """
        Resolves a deliverable strategy by type name or alias.
        Defaults to StudyNotesStrategy if unknown.
        """
        norm = (deliverable_type or "STUDY_NOTES").strip().upper()
        # Aliases mapping
        aliases = {
            "NOTES": "STUDY_NOTES",
            "STUDY": "STUDY_NOTES",
            "STUDY_NOTE": "STUDY_NOTES",
            "STUDY_NOTES": "STUDY_NOTES",
            "SUMMARIES": "SUMMARY",
            "EXECUTIVE_SUMMARY": "SUMMARY",
            "SUMMARY": "SUMMARY",
            "QUIZZES": "QUIZ",
            "PRACTICE_QUIZ": "QUIZ",
            "EXAM": "QUIZ",
            "QUIZ": "QUIZ",
            "FLASHCARD": "FLASHCARDS",
            "CARDS": "FLASHCARDS",
            "FLASHCARDS": "FLASHCARDS",
        }
        resolved_key = aliases.get(norm, norm)
        return self._strategies.get(resolved_key, self._strategies["STUDY_NOTES"])


# Singleton factory instance for dependency injection
default_deliverable_factory = DeliverableFactory()
