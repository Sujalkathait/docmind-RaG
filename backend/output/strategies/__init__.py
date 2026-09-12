from __future__ import annotations

from backend.output.strategies.base import DeliverableStrategy
from backend.output.strategies.study_notes import StudyNotesStrategy
from backend.output.strategies.summary import SummaryStrategy
from backend.output.strategies.quiz import QuizStrategy
from backend.output.strategies.flashcards import FlashcardsStrategy
from backend.output.strategies.factory import DeliverableFactory, default_deliverable_factory

__all__ = [
    "DeliverableStrategy",
    "StudyNotesStrategy",
    "SummaryStrategy",
    "QuizStrategy",
    "FlashcardsStrategy",
    "DeliverableFactory",
    "default_deliverable_factory",
]
