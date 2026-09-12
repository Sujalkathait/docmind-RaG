from __future__ import annotations

"""
DocMind RAG — Multi-Model Downloader Helper
Provides options to download various quantized GGUF models:
  - HuggingFaceTB/SmolLM2-360M-Instruct (Ultra-lightweight ~258 MB, fast on low RAM/CPU)
  - Qwen/Qwen2.5-3B-Instruct (Recommended CS tutor ~2.0 GB, deep reasoning & diagrams)
  - HuggingFaceTB/SmolLM2-1.7B-Instruct (Balanced ~1.0 GB)
  - Qwen/Qwen2.5-0.5B-Instruct (Compact ~468 MB)
  - Qwen/Qwen2.5-1.5B-Instruct (Mid-tier ~1.0 GB)
  - Custom Hugging Face GGUF direct URL
"""

import os

import sys
import time
import argparse
import urllib.request

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

OUTPUT_DIR = "models"

AVAILABLE_MODELS = {
    "1": {
        "id": "qwen2.5-3b",
        "name": "Qwen2.5 3B Instruct (Recommended CS Tutor)",
        "repo": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_str": "~2.0 GB",
        "description": "Deep reasoning, best for step-by-step algorithms, memory dry runs, and Mermaid diagrams.",
    },
    "2": {
        "id": "smollm2-360m",
        "name": "SmolLM2 360M Instruct (Ultra Lightweight for Cloud/Free Tier)",
        "repo": "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
        "filename": "SmolLM2-360M-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF/resolve/main/smollm2-360m-instruct-q4_k_m.gguf",
        "size_str": "~258 MB",
        "description": "Ultra fast, lightweight, runs easily on low RAM (512MB - 1GB) instances like Render.",
    },
}


def format_bytes(size: int | float) -> str:
    """Formats byte count to human-readable string."""
    size = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def download_model_file(
    url: str,
    output_filename: str,
    output_dir: str = OUTPUT_DIR,
    progress_callback=None,
) -> bool:
    """
    Downloads a GGUF model file with progress tracking.
    Can be used from CLI or imported by Streamlit.
    """
    os.makedirs(output_dir, exist_ok=True)
    target_path = os.path.join(output_dir, output_filename)

    if os.path.exists(target_path) and os.path.getsize(target_path) > 1024 * 1024:
        print(f"[INFO] Model already exists at: {target_path}")
        return True

    print("=" * 64)
    print(f"Downloading model: {output_filename}")
    print(f"Source URL: {url}")
    print(f"Target Path: {target_path}")
    print("=" * 64)

    start_time = time.time()

    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, (downloaded / total_size) * 100.0)
            elapsed = time.time() - start_time
            speed = downloaded / (elapsed if elapsed > 0 else 1)
            
            if progress_callback:
                progress_callback(percent, downloaded, total_size, speed)
            else:
                bar_len = 30
                filled_len = int(bar_len * percent / 100)
                bar = "#" * filled_len + "-" * (bar_len - filled_len)
                msg = (
                    f"\r[{bar}] {percent:5.1f}% | "
                    f"{format_bytes(downloaded)}/{format_bytes(total_size)} | "
                    f"{format_bytes(speed)}/s"
                )
                sys.stdout.write(msg)
                sys.stdout.flush()

    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")]
    urllib.request.install_opener(opener)

    try:
        urllib.request.urlretrieve(url, target_path, reporthook=report_progress)
        print("\n\n[SUCCESS] Download complete! Model is ready in models/ folder.")
        return True
    except KeyboardInterrupt:
        print("\n\n[WARNING] Download interrupted by user.")
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass
        return False
    except Exception as e:
        print(f"\n\n[ERROR] Download failed: {e}")
        if os.path.exists(target_path) and os.path.getsize(target_path) < 1024 * 1024:
            try:
                os.remove(target_path)
            except Exception:
                pass
        return False


def interactive_menu():
    """Interactive CLI menu to choose which model to download."""
    print("\n" + "=" * 64)
    print("🤖 DocMind RAG — Select LLM Model to Download")
    print("=" * 64)

    for key, info in AVAILABLE_MODELS.items():
        print(f"\n[{key}] {info['name']} ({info['size_str']})")
        print(f"    • Repo: {info['repo']}")
        print(f"    • Details: {info['description']}")

    print("\n" + "=" * 64)

    choice = input("\nEnter choice [1 or 2] (Default is 1 for SmolLM2 360M or 2 for Qwen 3B): ").strip()
    if not choice:
        choice = "1"

    if choice in AVAILABLE_MODELS:
        selected = AVAILABLE_MODELS[choice]
        print(f"\nSelected: {selected['name']}")
        download_model_file(selected["url"], selected["filename"])
    else:
        print(f"[ERROR] Invalid selection '{choice}'. Please choose 1 or 2.")


def main():
    parser = argparse.ArgumentParser(description="Download LLM models for DocMind RAG")
    parser.add_argument(
        "-m",
        "--model",
        choices=["smollm2-360m", "qwen2.5-3b"],
        help="Specify model ID to download directly without prompt",
    )
    parser.add_argument("--list", action="store_true", help="List all available models")
    parser.add_argument("--url", help="Download from a custom direct GGUF URL")
    parser.add_argument("--filename", help="Custom filename for downloaded GGUF")

    args = parser.parse_args()

    if args.list:
        print("\nAvailable Models:")
        for key, info in AVAILABLE_MODELS.items():
            print(f"  • {info['id']:15} : {info['name']} ({info['size_str']})")
        return

    if args.url:
        fname = args.filename or os.path.basename(args.url.split("?")[0])
        if not fname.endswith(".gguf"):
            fname += ".gguf"
        download_model_file(args.url, fname)
        return

    if args.model:
        for info in AVAILABLE_MODELS.values():
            if info["id"] == args.model:
                download_model_file(info["url"], info["filename"])
                return

    # No arguments given -> launch interactive menu
    interactive_menu()


if __name__ == "__main__":
    main()
