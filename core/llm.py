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


def _get_optimal_threads() -> int:
    """Calculates optimal CPU thread count for fast inference without cache thrashing."""
    if N_THREADS > 0:
        return N_THREADS
    cpu_cnt = os.cpu_count() or 4
    # Sweet spot for llama.cpp on multi-core CPUs is 6-8 threads
    if cpu_cnt >= 8:
        return min(8, cpu_cnt - 2)
    elif cpu_cnt >= 6:
        return min(6, cpu_cnt - 1)
    else:
        return max(2, cpu_cnt)


def _get_model() -> Any:
    """Lazily loads and permanently caches the GGUF model in RAM."""
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

    n_threads = _get_optimal_threads()

    _llm = Llama(
        model_path=effective_path,
        n_ctx=N_CTX,
        n_gpu_layers=N_GPU_LAYERS,
        n_batch=N_BATCH,
        n_threads=n_threads,
        n_threads_batch=n_threads,
        use_mmap=True,
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
        "n_threads": _get_optimal_threads(),
    }


def get_dynamic_max_tokens(prompt: str) -> int:
    """
    Dynamically sizes MAX_TOKENS (256 - 1024) based on query complexity.
    Prevents CPU rambling and cuts generation time by up to 75%.
    """
    p_lower = prompt.lower().strip()
    
    # 1. Short / Direct / Output / Definition queries (256 - 384 tokens)
    short_triggers = [
        "what is", "define", "definition", "meaning of", "output", "what does",
        "short", "brief", "one line", "name the", "list the", "who is", "which is",
        "syntax", "what are the"
    ]
    if any(p_lower.startswith(t) or f" {t} " in p_lower for t in short_triggers):
        if "detailed" not in p_lower and "explain" not in p_lower and "code and" not in p_lower:
            return 384

    # 2. Deep / Exam / Multi-part / Comprehensive queries (768 - 1024 tokens)
    complex_triggers = [
        "detailed", "deep explanation", "in detail", "explain step by step",
        "exam answer", "5 marks", "10 marks", "code and dry run", "dry run and code",
        "implement and", "comprehensive", "full tutorial", "write a complete"
    ]
    if any(t in p_lower for t in complex_triggers):
        return 1024

    # 3. Standard queries (Explanation, difference, dry run, single code snippet) (512 tokens)
    return 512


def _assemble_chatml(
    question: str,
    context: str = "",
    history: list[dict] | None = None,
    model_path: str = "",
) -> str:
    """
    Assembles prompt into ChatML format with concise system prompt,
    relevant context, and minimal historical turns.
    """
    effective_model = model_path or get_effective_model_path()
    system_prompt = get_system_prompt(effective_model)
    is_smollm = "smollm" in effective_model.lower() or "360m" in effective_model.lower()

    if context:
        user_content = f"Context from study notes:\n{context}\n\n{question}"
    else:
        user_content = question

    # System prompt turn
    turns = [f"<|im_start|>system\n{system_prompt}<|im_end|>\n"]

    # Append minimal recent conversation turns (last 2 turns max: 1 user + 1 assistant)
    if history:
        recent_history = history[-2:]
        for msg in recent_history:
            role = msg.get("role")
            content = msg.get("content", "").strip()
            if role in ("user", "assistant") and content:
                # Truncate prior assistant answers to avoid re-evaluating long outputs
                max_hist_len = 180 if is_smollm else 250
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
    Fast budget check: ensures (prompt_tokens + max_tokens) <= N_CTX.
    Avoids repeated slow llm.tokenize() calls via character-length heuristics.
    """
    if not context:
        return ""

    # Safe headroom
    max_allowed_prompt_tokens = max(512, N_CTX - max_tokens - 64)
    max_allowed_chars = int(max_allowed_prompt_tokens * 3.2)

    test_prompt = _assemble_chatml(question, context, history, model_path=model_path)
    
    # Fast path: character count is well within safety margin
    if len(test_prompt) <= max_allowed_chars:
        return context

    # Precise single-pass tokenization check
    prompt_tokens = len(llm.tokenize(test_prompt.encode("utf-8")))
    if prompt_tokens <= max_allowed_prompt_tokens:
        return context

    # Over budget: progressively drop chunks from the bottom
    chunks = context.split("\n\n---\n\n")
    while len(chunks) > 1:
        chunks.pop()
        trimmed = "\n\n---\n\n".join(chunks)
        test_prompt = _assemble_chatml(question, trimmed, history, model_path=model_path)
        if len(test_prompt) <= max_allowed_chars:
            return trimmed
        if len(llm.tokenize(test_prompt.encode("utf-8"))) <= max_allowed_prompt_tokens:
            return trimmed

    if chunks:
        single = chunks[0]
        if len(single) > 400:
            single = single[:400]
        return single

    return ""


def generate(
    prompt: str,
    context: str = "",
    history: list[dict] | None = None,
    max_tokens: int | None = None,
    temperature: float = TEMPERATURE,
    stream: bool = False,
    **kwargs,
):
    """
    Generates a response using active GGUF model with dynamic token scaling and context budgeting.
    """
    llm = _get_model()
    effective_path = get_effective_model_path()

    # Dynamic token sizing if not explicitly supplied
    effective_max_tokens = max_tokens if max_tokens is not None else get_dynamic_max_tokens(prompt)

    # Trim context if needed
    budgeted_context = _trim_context_to_budget(
        llm, prompt, context, effective_max_tokens, history, model_path=effective_path
    )

    # Build the full ChatML prompt
    full_prompt = _assemble_chatml(prompt, budgeted_context, history, model_path=effective_path)

    if stream:
        return _stream_generate(llm, full_prompt, effective_max_tokens, temperature)
    else:
        return _batch_generate(llm, full_prompt, effective_max_tokens, temperature)


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
