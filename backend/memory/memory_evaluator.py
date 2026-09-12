from __future__ import annotations

"""
DocMind Second Brain — Memory Evaluator & Safety Distillation Filter
Scans conversational turns for durable preferences or goals while strictly rejecting secrets and transient chitchat.
"""

import re
from typing import Optional, Dict, Any, Tuple
from backend.database.models import MemoryCategory
from backend.database.crud import upsert_memory

# Security patterns that must NEVER be saved to persistent memory
SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",                  # OpenAI/general API keys
    r"ghp_[a-zA-Z0-9]{36}",                   # GitHub tokens
    r"bearer\s+[a-zA-Z0-9_\-\.]{20,}",       # Auth bearer tokens
    r"password\s*[:=]\s*\S+",                # Passwords
    r"passwd\s*[:=]\s*\S+",
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", # Emails (PII)
    r"\b(?:\d{4}[ -]?){3}\d{4}\b",           # Credit card patterns
]

# Preference signals in user inputs
PREFERENCE_TRIGGERS = [
    (r"always\s+(?:explain|show|give|format|use|provide)\s+(.+)", MemoryCategory.LEARNING_PREFERENCE, "style", 0.85),
    (r"i\s+(?:prefer|like|want)\s+(.+)", MemoryCategory.USER_PREFERENCE, "preference", 0.75),
    (r"from\s+now\s+on\s*,\s*(.+)", MemoryCategory.USER_PREFERENCE, "instruction", 0.80),
    (r"my\s+goal\s+is\s+(?:to\s+)?(.+)", MemoryCategory.USER_GOAL, "primary_goal", 0.85),
    (r"i\s+am\s+studying\s+(?:for\s+)?(.+)", MemoryCategory.PROJECT_CONTEXT, "subject", 0.80),
    (r"explain\s+(?:in|using)\s+([a-zA-Z0-9_#+]+)\s+first", MemoryCategory.LEARNING_PREFERENCE, "code_lang", 0.90),
    (r"use\s+([a-zA-Z0-9_#+]+)\s+instead\s+of\s+([a-zA-Z0-9_#+]+)", MemoryCategory.LEARNING_PREFERENCE, "preferred_tech", 0.85),
]


def scrub_secrets(text: str) -> Tuple[bool, str]:
    """
    Checks for sensitive tokens/passwords.
    Returns (has_secrets, clean_or_redacted_text).
    """
    cleaned = text
    has_secret = False
    for pat in SECRET_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            has_secret = True
            cleaned = re.sub(pat, "[REDACTED_SECRET]", cleaned, flags=re.IGNORECASE)
    return has_secret, cleaned


def evaluate_interaction_for_memory(
    user_message: str,
    assistant_response: str = "",
    user_id: str = "default_user",
    project_id: str = "DEFAULT",
) -> Optional[Dict[str, Any]]:
    """
    Evaluates whether an interaction contains an enduring user preference or goal.
    Returns memory dict if successfully extracted and saved, else None.
    """
    msg_clean = user_message.strip()
    if len(msg_clean) < 10:
        return None

    # 1. Security Check
    has_secret, safe_msg = scrub_secrets(msg_clean)
    if has_secret:
        # Never store messages containing secrets
        return None

    # 2. Transient Check (Skip chit-chat)
    lower_msg = safe_msg.lower()
    chitchat = ["hello", "hi", "hey", "thanks", "thank you", "bye", "goodbye", "ok", "okay", "yes", "no"]
    if lower_msg in chitchat or lower_msg.startswith(("can you hear", "test")):
        return None

    # 3. Detect Explicit Preferences
    for pattern, category, key_prefix, base_importance in PREFERENCE_TRIGGERS:
        match = re.search(pattern, safe_msg, re.IGNORECASE)
        if match:
            extracted_val = match.group(1).strip()
            # Clean punctuation from end
            extracted_val = re.sub(r"[.!?]+$", "", extracted_val).strip()

            if len(extracted_val) >= 3 and len(extracted_val) <= 150:
                mem_key = f"{key_prefix}_{extracted_val[:20].lower().replace(' ', '_')}"
                mem = upsert_memory(
                    user_id=user_id,
                    category=category,
                    key=mem_key,
                    value=extracted_val,
                    importance_score=base_importance,
                    project_id=project_id,
                )
                return {
                    "action": "saved",
                    "id": mem.id,
                    "category": mem.category,
                    "key": mem.memory_key,
                    "value": mem.memory_value,
                    "importance": mem.importance_score,
                }

    return None
