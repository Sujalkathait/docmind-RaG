from __future__ import annotations

"""
DocMind Second Brain — Prompt Builder (Builder Pattern / SRP)
Provides a fluent builder interface for assembling multi-layered grounded prompts
with token budgeting and ChatML formatting.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os


class BasePromptBuilder(ABC):
    """Abstract Builder interface for prompt construction."""

    @abstractmethod
    def set_system_instructions(self, instructions: str) -> BasePromptBuilder:
        pass

    @abstractmethod
    def add_rules(self, rules: str) -> BasePromptBuilder:
        pass

    @abstractmethod
    def add_memories(self, memories: List[str]) -> BasePromptBuilder:
        pass

    @abstractmethod
    def add_evidence(self, chunks: List[str]) -> BasePromptBuilder:
        pass

    @abstractmethod
    def add_wiki_concepts(self, concepts: List[Dict[str, Any]]) -> BasePromptBuilder:
        pass

    @abstractmethod
    def add_history(self, history: List[Dict[str, str]]) -> BasePromptBuilder:
        pass

    @abstractmethod
    def set_query(self, query: str) -> BasePromptBuilder:
        pass

    @abstractmethod
    def build(self) -> str:
        pass

    @abstractmethod
    def build_messages(self) -> List[Dict[str, str]]:
        pass


class ChatMLPromptBuilder(BasePromptBuilder):
    """
    Concrete fluent Builder for ChatML format prompts:
    <|im_start|>system\n...\n<|im_end|>\n<|im_start|>user\n...\n<|im_end|>
    """

    def __init__(self):
        self._system_instructions: str = ""
        self._rules: str = ""
        self._memories: List[str] = []
        self._evidence_chunks: List[str] = []
        self._wiki_concepts: List[str] = []
        self._history: List[Dict[str, str]] = []
        self._query: str = ""
        self._max_budget: int = 4096

    def set_system_instructions(self, instructions: str) -> ChatMLPromptBuilder:
        self._system_instructions = instructions.strip()
        return self

    def add_rules(self, rules: str) -> ChatMLPromptBuilder:
        self._rules = rules.strip()
        return self

    def add_memories(self, memories: List[str]) -> ChatMLPromptBuilder:
        self._memories.extend([m.strip() for m in memories if m and m.strip()])
        return self

    def add_evidence(self, chunks: List[str]) -> ChatMLPromptBuilder:
        self._evidence_chunks.extend([c.strip() for c in chunks if c and c.strip()])
        return self

    def add_wiki_concepts(self, concepts: List[Dict[str, Any]]) -> ChatMLPromptBuilder:
        for c in concepts:
            name = c.get("name", "")
            definition = c.get("definition", "")
            if name:
                self._wiki_concepts.append(f"• {name}: {definition}" if definition else f"• {name}")
        return self

    def add_history(self, history: List[Dict[str, str]]) -> ChatMLPromptBuilder:
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if content:
                self._history.append({"role": role, "content": content})
        return self

    def set_query(self, query: str) -> ChatMLPromptBuilder:
        self._query = query.strip()
        return self

    def set_budget(self, max_tokens: int) -> ChatMLPromptBuilder:
        self._max_budget = max(512, max_tokens)
        return self

    def _assemble_system_block(self) -> str:
        parts = []
        if self._system_instructions:
            parts.append(self._system_instructions)
        if self._rules:
            parts.append(f"CORE GROUNDING RULES:\n{self._rules}")
        if self._memories:
            parts.append("USER PREFERENCES & CONTEXT:\n" + "\n".join(f"- {m}" for m in self._memories))
        return "\n\n".join(parts)

    def _assemble_context_block(self) -> str:
        parts = []
        if self._evidence_chunks:
            parts.append("PRIMARY DOCUMENT EVIDENCE (Source of Truth):\n" + "\n\n---\n\n".join(self._evidence_chunks))
        if self._wiki_concepts:
            parts.append("WIKI KNOWLEDGE CONNECTIONS:\n" + "\n".join(self._wiki_concepts))
        return "\n\n====================\n\n".join(parts)

    def build_messages(self) -> List[Dict[str, str]]:
        """Builds standard OpenAI-compatible messages array."""
        messages: List[Dict[str, str]] = []

        system_content = self._assemble_system_block()
        if system_content:
            messages.append({"role": "system", "content": system_content})

        for turn in self._history:
            messages.append(turn)

        # Context + Query in current user turn
        context_content = self._assemble_context_block()
        user_body = []
        if context_content:
            user_body.append(f"Study Material Context:\n{context_content}")
        user_body.append(f"Question: {self._query}" if self._query else "")

        messages.append({"role": "user", "content": "\n\n".join(filter(None, user_body))})
        return messages

    def build(self) -> str:
        """Renders full ChatML text for token-budgeted local LLM inference."""
        system_content = self._assemble_system_block()
        prompt_lines = [f"<|im_start|>system\n{system_content}<|im_end|>"]

        for turn in self._history:
            prompt_lines.append(f"<|im_start|>{turn['role']}\n{turn['content']}<|im_end|>")

        context_content = self._assemble_context_block()
        user_parts = []
        if context_content:
            user_parts.append(f"Study Material Context:\n{context_content}")
        user_parts.append(f"Question: {self._query}" if self._query else "")

        user_content = "\n\n".join(filter(None, user_parts))
        prompt_lines.append(f"<|im_start|>user\n{user_content}<|im_end|>")
        prompt_lines.append("<|im_start|>assistant\n")

        return "\n".join(prompt_lines)
