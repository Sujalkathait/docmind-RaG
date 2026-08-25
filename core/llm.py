from __future__ import annotations

import os
import glob
from typing import Any

try:
    from llama_cpp import Llama
    _HAS_LLAMA_CPP = True
except ImportError:
    Llama = None
    _HAS_LLAMA_CPP = False

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
    get_system_prompt,
)

# Singleton Llama model instance & active model override
_llm: Any = None
_active_model_path: str | None = None


def get_available_models() -> list[dict]:
    """Scans the models/ directory for all available .gguf model files."""
    models_dir = os.path.dirname(MODEL_PATH) if os.path.dirname(MODEL_PATH) else "models"
    if not os.path.exists(models_dir):
        return []
    
    gguf_files = glob.glob(os.path.join(models_dir, "*.gguf"))
    results = []
    for fpath in sorted(gguf_files):
        fname = os.path.basename(fpath)
        try:
            size_bytes = os.path.getsize(fpath)
            size_mb = size_bytes / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{size_mb / 1024:.2f} GB"
        except Exception:
            size_bytes = 0
            size_str = "Unknown"

        results.append({
            "name": fname,
            "path": fpath,
            "size_bytes": size_bytes,
            "size_str": size_str,
        })
    return results


def set_active_model(model_name_or_path: str) -> bool:
    """Dynamically sets and switches the active model file."""
    global _llm, _active_model_path
    
    models_dir = os.path.dirname(MODEL_PATH) if os.path.dirname(MODEL_PATH) else "models"
    if os.path.isabs(model_name_or_path) or os.path.exists(model_name_or_path):
        target_path = model_name_or_path
    else:
        target_path = os.path.join(models_dir, model_name_or_path)

    if os.path.exists(target_path):
        if _active_model_path != target_path:
            _active_model_path = target_path
            _llm = None  # Reset singleton to reload on next inference
        return True
    return False


def unload_model() -> None:
    """Explicitly unloads the model from memory."""
    global _llm
    _llm = None


def get_effective_model_path() -> str:
    """
    Returns the user-selected active model path, configured MODEL_PATH,
    or auto-detects any .gguf model present in the models/ directory.
    """
    global _active_model_path
    if _active_model_path and os.path.exists(_active_model_path):
        return _active_model_path

    if os.path.exists(MODEL_PATH):
        return MODEL_PATH

    models_dir = os.path.dirname(MODEL_PATH) if os.path.dirname(MODEL_PATH) else "models"
    if os.path.exists(models_dir):
        gguf_files = glob.glob(os.path.join(models_dir, "*.gguf"))
        if gguf_files:
            return gguf_files[0]

    return MODEL_PATH


def _get_model() -> Any:
    """Lazily loads and caches the GGUF model with configured context window."""
    global _llm
    if not _HAS_LLAMA_CPP or Llama is None:
        raise ImportError(
            "llama-cpp-python is not installed. Please install llama-cpp-python to run DocMind RAG."
        )

    effective_path = get_effective_model_path()
    if not os.path.exists(effective_path):
        raise FileNotFoundError(
            f"GGUF model not found at '{effective_path}'.\n"
            f"Download a model (e.g. SmolLM2-360M or Qwen2.5-3B) by running `python download_model.py`."
        )

    if _llm is not None:
        try:
            if _llm.n_ctx() == N_CTX:
                return _llm
        except Exception:
            return _llm

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
    """Check if the model file exists and llama-cpp-python is available."""
    return _HAS_LLAMA_CPP and os.path.exists(get_effective_model_path())


def get_model_info() -> dict:
    """Returns model configuration info for the UI status display."""
    effective_path = get_effective_model_path()
    available = get_available_models()
    return {
        "model_path": effective_path,
        "model_name": os.path.basename(effective_path) if effective_path else "None",
        "exists": os.path.exists(effective_path),
        "has_llama_cpp": _HAS_LLAMA_CPP,
        "is_ready": is_model_loaded(),
        "available_models": available,
        "n_ctx": N_CTX,
        "n_gpu_layers": N_GPU_LAYERS,
        "n_batch": N_BATCH,
    }


def _assemble_chatml(
    question: str,
    context: str = "",
    history: list[dict] | None = None,
    model_path: str = "",
) -> str:
    """Assembles prompt into ChatML format with model-specific system prompt and multi-turn history."""
    effective_model = model_path or get_effective_model_path()
    system_prompt = get_system_prompt(effective_model)
    is_smollm = "smollm" in effective_model.lower() or "360m" in effective_model.lower()

    if context:
        user_content = f"Context from study notes:\n{context}\n\n{question}"
    else:
        user_content = question

    # Multi-turn ChatML turns
    turns = [f"<|im_start|>system\n{system_prompt}<|im_end|>\n"]

    # Append recent conversation turns (up to last 6 turns)
    if history:
        recent_history = history[-6:]
        for msg in recent_history:
            role = msg.get("role")
            content = msg.get("content", "").strip()
            if role in ("user", "assistant") and content:
                # Truncate very long previous responses to conserve token budget
                max_hist_len = 600 if is_smollm else 1200
                if len(content) > max_hist_len:
                    content = content[:max_hist_len] + "..."
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
    model_path: str = "",
) -> str:
    """
    Ensures that (prompt_tokens + max_tokens) <= N_CTX.
    If context is too large, trims chunks progressively from the bottom.
    """
    if not context:
        return ""

    test_prompt = _assemble_chatml(question, context, history, model_path=model_path)
    prompt_tokens = len(llm.tokenize(test_prompt.encode("utf-8")))

    # Safe budget: leave at least max_tokens + 64 tokens headroom
    max_allowed_prompt_tokens = max(512, N_CTX - max_tokens - 64)

    if prompt_tokens <= max_allowed_prompt_tokens:
        return context

    chunks = context.split("\n\n---\n\n")
    while len(chunks) > 1:
        chunks.pop()
        trimmed = "\n\n---\n\n".join(chunks)
        test_prompt = _assemble_chatml(question, trimmed, history, model_path=model_path)
        if len(llm.tokenize(test_prompt.encode("utf-8"))) <= max_allowed_prompt_tokens:
            return trimmed

    if chunks:
        single = chunks[0]
        while len(single) > 200:
            single = single[: int(len(single) * 0.75)]
            test_prompt = _assemble_chatml(question, single, history, model_path=model_path)
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
    Generates a response using active GGUF model with multi-turn history and context budgeting.
    """
    llm = _get_model()
    effective_path = get_effective_model_path()

    # Trim context if needed to strictly protect generation budget
    budgeted_context = _trim_context_to_budget(llm, prompt, context, max_tokens, history, model_path=effective_path)

    # Build the full multi-turn ChatML prompt with tailored system prompt
    full_prompt = _assemble_chatml(prompt, budgeted_context, history, model_path=effective_path)

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
