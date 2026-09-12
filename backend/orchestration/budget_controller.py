from __future__ import annotations

"""
DocMind Second Brain — Context Budget Controller
Enforces token budgeting for local LLM context window (N_CTX = 4096).
Prevents context overflow while preserving room for high-speed local generation.
"""

from typing import Dict, Any, List

# Token budget ceilings for N_CTX = 4096
DEFAULT_N_CTX = 4096

BUDGET_RULES = 350       # System prompt & anti-hallucination directives
BUDGET_MEMORIES = 150    # Active user & learning preferences
BUDGET_WIKI = 250        # Structured Wiki knowledge & graph relationships
BUDGET_HISTORY = 300     # Recent conversation history turns
BUDGET_CHUNKS = 1800     # Primary document evidence chunks
BUDGET_HEADROOM = 1024   # Reserved generation headroom for LLM response


def estimate_tokens(text: str) -> int:
    """Fast character-based token estimation (average ~3.8 chars per token for English & code)."""
    if not text:
        return 0
    return max(1, int(len(text) / 3.8))


def trim_to_token_budget(text: str, max_tokens: int) -> str:
    """Trims text to approximate max token budget while respecting sentence boundaries."""
    if not text:
        return ""
    cur_tokens = estimate_tokens(text)
    if cur_tokens <= max_tokens:
        return text

    # Proportionally slice
    char_limit = int(max_tokens * 3.8)
    truncated = text[:char_limit]
    # Try to break at last newline or period
    last_break = max(truncated.rfind("\n"), truncated.rfind(". "))
    if last_break > int(char_limit * 0.7):
        return truncated[:last_break] + "..."
    return truncated + "..."


def allocate_context_budget(
    evidence_chunks: List[str],
    wiki_context: str,
    memory_context: str,
    history_turns: List[Dict[str, str]],
    n_ctx: int = DEFAULT_N_CTX,
) -> Dict[str, Any]:
    """
    Allocates and validates token budgets across all context components.
    Ensures total prompt tokens + generation headroom <= n_ctx.
    """
    clean_wiki = trim_to_token_budget(wiki_context, BUDGET_WIKI)
    clean_mem = trim_to_token_budget(memory_context, BUDGET_MEMORIES)

    # Budget document chunks
    selected_chunks = []
    chunk_tokens = 0
    for chk in evidence_chunks:
        chk_tok = estimate_tokens(chk)
        if chunk_tokens + chk_tok <= BUDGET_CHUNKS:
            selected_chunks.append(chk)
            chunk_tokens += chk_tok
        else:
            remaining_budget = BUDGET_CHUNKS - chunk_tokens
            if remaining_budget > 60:
                selected_chunks.append(trim_to_token_budget(chk, remaining_budget))
            break

    # Budget history (take most recent turns)
    selected_history = []
    hist_tokens = 0
    for turn in reversed(history_turns):
        turn_text = f"{turn.get('role', '')}: {turn.get('content', '')}"
        tok = estimate_tokens(turn_text)
        if hist_tokens + tok <= BUDGET_HISTORY:
            selected_history.insert(0, turn)
            hist_tokens += tok
        else:
            break

    total_prompt_estimate = (
        BUDGET_RULES
        + estimate_tokens(clean_mem)
        + estimate_tokens(clean_wiki)
        + chunk_tokens
        + hist_tokens
    )

    return {
        "budgeted_chunks": selected_chunks,
        "budgeted_wiki": clean_wiki,
        "budgeted_memory": clean_mem,
        "budgeted_history": selected_history,
        "estimated_prompt_tokens": total_prompt_estimate,
        "available_generation_tokens": max(256, n_ctx - total_prompt_estimate),
    }
