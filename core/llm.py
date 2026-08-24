from __future__ import annotations

import os
import glob
from llama_cpp import Llama

from config import (
    MODEL_PATH,
    N_CTX,
    N_GPU_LAYERS,
    N_BATCH,
    N_THREADS,
    MAX_TOKENS,
    TEMPERATURE,
    TOP_P,
    REPEAT_PENALTY,
    SYSTEM_PROMPT,
)

# Singleton Llama model
_llm: Llama | None = None


def get_effective_model_path() -> str:
    """
    Returns the configured MODEL_PATH if it exists,
    or auto-detects any .gguf model present in the models/ directory.
    """
    if os.path.exists(MODEL_PATH):
        return MODEL_PATH

    models_dir = os.path.dirname(MODEL_PATH) if os.path.dirname(MODEL_PATH) else "models"
    if os.path.exists(models_dir):
        gguf_files = glob.glob(os.path.join(models_dir, "*.gguf"))
        if gguf_files:
            return gguf_files[0]

    return MODEL_PATH


def _get_model() -> Llama:
    """Lazily loads and caches the Qwen GGUF model with configured context window."""
    global _llm
    if _llm is not None:
        try:
            if _llm.n_ctx() == N_CTX:
                return _llm
        except Exception:
            return _llm

    effective_path = get_effective_model_path()
    if not os.path.exists(effective_path):
        raise FileNotFoundError(
            f"GGUF model not found at '{effective_path}'.\n"
            f"Download Qwen2.5-3B-Instruct-Q4_K_M.gguf from Hugging Face and place it in the 'models/' directory.\n"
            f"See README.md for instructions."
        )

    n_threads = N_THREADS if N_THREADS > 0 else max(4, (os.cpu_count() or 4) - 2)

    _llm = Llama(
        model_path=effective_path,
        n_ctx=N_CTX,
        n_gpu_layers=N_GPU_LAYERS,
        n_batch=N_BATCH,
        n_threads=n_threads,
        verbose=False,
    )

    return _llm


def is_model_loaded() -> bool:
    """Check if the model file exists and is ready."""
    return os.path.exists(get_effective_model_path())


def get_model_info() -> dict:
    """Returns model configuration info for the UI status display."""
    effective_path = get_effective_model_path()
    return {
        "model_path": effective_path,
        "exists": os.path.exists(effective_path),
        "n_ctx": N_CTX,
        "n_gpu_layers": N_GPU_LAYERS,
        "n_batch": N_BATCH,
    }


def _assemble_chatml(
    question: str,
    context: str = "",
    history: list[dict] | None = None,
) -> str:
    """Assembles prompt into Qwen ChatML format with multi-turn conversational history."""
    is_dry_run = any(
        kw in question.lower()
        for kw in ("dry run", "dryrun", "trace", "step by step", "step-by-step", "with values", "trace table", "tracing")
    )

    instructions = [
        "- Answer proportionately to the question (jitna question, us hisaab se answer).",
        "- Conversational Continuity: Maintain full context of the ongoing conversation in this chat session. When the user asks a follow-up or continues an earlier topic, NEVER jump away from the previous problem until it is fully resolved. Connect answers directly to what was previously discussed.",
    ]

    if is_dry_run:
        instructions.append(
            "- The user requested a DRY RUN: You MUST provide (1) working code, (2) sample initial values, (3) a complete Step-by-Step Markdown Trace Table tracking line, variable states (Before -> After), conditions, and stack/memory states at every step, (4) visual/ASCII memory transition, and (5) time & space complexity. Never summarize or omit steps."
        )
    else:
        instructions.extend([
            "- For short/direct questions, give a direct, clear, concise answer with a simple diagram if helpful.",
            "- For in-depth/detailed questions, provide a full pedagogical breakdown with code and complexity.",
        ])

    instructions.append(
        "- If generating a Mermaid diagram, keep it valid and properly closed (e.g. A[\"Label\"] --> B[\"Label\"])."
    )

    if context:
        instructions.append("- Base your answer primarily on the provided PDF context.")
        user_content = (
            f"Here is the context retrieved from the user's PDF documents:\n"
            f"==================================================\n"
            f"{context}\n"
            f"==================================================\n\n"
            f"User Question:\n{question}\n\n"
            f"Instructions:\n" + "\n".join(instructions) + "\n\nAnswer:"
        )
    else:
        user_content = (
            f"User Question:\n{question}\n\n"
            f"Instructions:\n" + "\n".join(instructions) + "\n\nAnswer:"
        )

    # Multi-turn ChatML turns
    turns = [f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"]

    # Append recent conversation turns (up to last 6 turns)
    if history:
        recent_history = history[-6:]
        for msg in recent_history:
            role = msg.get("role")
            content = msg.get("content", "").strip()
            if role in ("user", "assistant") and content:
                # Truncate very long previous responses to conserve token budget
                if len(content) > 1200:
                    content = content[:1200] + "..."
                turns.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")

    # Current query turn
    turns.append(f"<|im_start|>user\n{user_content}<|im_end|>\n<|im_start|>assistant\n")

    return "".join(turns)


def _trim_context_to_budget(
    llm: Llama,
    question: str,
    context: str,
    max_tokens: int,
    history: list[dict] | None = None,
) -> str:
    """
    Ensures that (prompt_tokens + max_tokens) <= N_CTX.
    If context is too large, trims chunks progressively from the bottom.
    """
    if not context:
        return ""

    test_prompt = _assemble_chatml(question, context, history)
    prompt_tokens = len(llm.tokenize(test_prompt.encode("utf-8")))

    # Safe budget: leave at least max_tokens + 64 tokens headroom
    max_allowed_prompt_tokens = max(512, N_CTX - max_tokens - 64)

    if prompt_tokens <= max_allowed_prompt_tokens:
        return context

    chunks = context.split("\n\n---\n\n")
    while len(chunks) > 1:
        chunks.pop()
        trimmed = "\n\n---\n\n".join(chunks)
        test_prompt = _assemble_chatml(question, trimmed, history)
        if len(llm.tokenize(test_prompt.encode("utf-8"))) <= max_allowed_prompt_tokens:
            return trimmed

    if chunks:
        single = chunks[0]
        while len(single) > 200:
            single = single[: int(len(single) * 0.75)]
            test_prompt = _assemble_chatml(question, single, history)
            if len(llm.tokenize(test_prompt.encode("utf-8"))) <= max_allowed_prompt_tokens:
                return single

    return ""


def generate(
    prompt: str,
    context: str = "",
    history: list[dict] | None = None,
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
    stream: bool = False,
    **kwargs,
):
    """
    Generates a response using Qwen GGUF model with multi-turn history and context budgeting.

    Args:
        prompt: The user's question
        context: Retrieved RAG context chunks
        history: Prior conversation turns list of dicts [{'role': 'user'|'assistant', 'content': '...'}]
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        stream: If True, returns a generator yielding token strings

    Returns:
        str if stream=False, generator of str if stream=True
    """
    llm = _get_model()

    # Trim context if needed to strictly protect generation budget
    budgeted_context = _trim_context_to_budget(llm, prompt, context, max_tokens, history)

    # Build the full multi-turn ChatML prompt
    full_prompt = _assemble_chatml(prompt, budgeted_context, history)

    if stream:
        return _stream_generate(llm, full_prompt, max_tokens, temperature)
    else:
        return _batch_generate(llm, full_prompt, max_tokens, temperature)


def _batch_generate(
    llm: Llama, prompt: str, max_tokens: int, temperature: float
) -> str:
    """Generates a complete response (non-streaming)."""
    output = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=TOP_P,
        repeat_penalty=REPEAT_PENALTY,
        stop=["<|im_end|>", "<|im_start|>"],
        echo=False,
    )

    text = output["choices"][0]["text"].strip()
    return text


def _stream_generate(
    llm: Llama, prompt: str, max_tokens: int, temperature: float
):
    """Yields tokens one at a time for streaming display."""
    stream = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=TOP_P,
        repeat_penalty=REPEAT_PENALTY,
        stop=["<|im_end|>", "<|im_start|>"],
        echo=False,
        stream=True,
    )

    for chunk in stream:
        token = chunk["choices"][0]["text"]
        if token:
            yield token
