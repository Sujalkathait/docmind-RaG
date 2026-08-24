"""
DocMind RAG — Model Downloader Helper
Downloads the recommended Qwen GGUF model directly to the models/ folder with real-time progress.
"""

import os
import sys
import urllib.request
import time

MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"
OUTPUT_DIR = "models"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "qwen2.5-3b-instruct-q4_k_m.gguf")


def format_bytes(size: int) -> str:
    """Formats byte count to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def download_with_progress():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if os.path.exists(OUTPUT_FILE):
        print(f"✅ Model already exists at: {OUTPUT_FILE}")
        return

    print("=" * 60)
    print("📥 Downloading Qwen2.5-3B-Instruct GGUF model (~2.1 GB)...")
    print(f"Source: {MODEL_URL}")
    print(f"Target: {OUTPUT_FILE}")
    print("=" * 60)

    start_time = time.time()

    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, (downloaded / total_size) * 100.0)
            elapsed = time.time() - start_time
            speed = downloaded / (elapsed if elapsed > 0 else 1)
            bar_len = 30
            filled_len = int(bar_len * percent / 100)
            bar = "█" * filled_len + "░" * (bar_len - filled_len)
            msg = (
                f"\r[{bar}] {percent:5.1f}% | "
                f"{format_bytes(downloaded)}/{format_bytes(total_size)} | "
                f"{format_bytes(speed)}/s"
            )
            sys.stdout.write(msg)
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(MODEL_URL, OUTPUT_FILE, reporthook=report_progress)
        print("\n\n✅ Download complete! The model is ready to use.")
    except KeyboardInterrupt:
        print("\n\n⚠️ Download interrupted.")
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
    except Exception as e:
        print(f"\n\n❌ Download failed: {e}")
        print("You can also download manually or use curl.exe (see README.md).")


if __name__ == "__main__":
    download_with_progress()
