#!/usr/bin/env python3
"""
DocMind RAG + Second Brain — Main Unified Launcher
100% Offline, Zero API Keys, Local GGUF LLM Execution.

Usage:
  python run.py         # Runs unified server (FastAPI backend + React UI) on http://127.0.0.1:8000
  python run.py --dev   # Runs hot-reloading dev servers (FastAPI on 8000 + Vite on 5173)
"""

from __future__ import annotations

import sys
import os
import threading
import time
import subprocess
import webbrowser
from pathlib import Path

# Silence external API / Hub warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Reconfigure stdout/stderr to UTF-8 if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"


def ensure_frontend_built():
    """Verify frontend build exists, or automatically build it."""
    if not (DIST_DIR / "index.html").exists():
        print("=" * 65)
        print("  [DocMind] Frontend bundle not found. Building React app...")
        print("=" * 65)

        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

        if not (FRONTEND_DIR / "node_modules").exists():
            print("  -> Installing frontend dependencies (npm install)...")
            res = subprocess.run([npm_cmd, "install"], cwd=str(FRONTEND_DIR))
            if res.returncode != 0:
                print("  [WARN] npm install had issues. Attempting build anyway...")

        print("  -> Building production bundle (npm run build)...")
        build_res = subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR))
        if build_res.returncode == 0:
            print("  [OK] React build successful! Files in frontend/dist")
        else:
            print("  [WARN] npm build failed. Backend will serve API in headless mode.")
    else:
        print("  [OK] React production bundle ready in frontend/dist")


def open_browser_delayed(url: str, delay_seconds: float = 1.5):
    """Opens browser tab after server initializes."""
    def _open():
        time.sleep(delay_seconds)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()


def run_dev_mode():
    """Runs concurrent hot-reloading development servers."""
    print("=" * 65)
    print("  DocMind RAG + Second Brain — Development Mode")
    print("  Backend API:  http://127.0.0.1:8000 (auto-reload)")
    print("  Vite React:   http://localhost:5173 (HMR enabled)")
    print("=" * 65)

    python_exec = sys.executable
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    backend_proc = subprocess.Popen(
        [python_exec, "-m", "uvicorn", "backend.api.main:app", "--reload", "--port", "8000"],
        cwd=str(ROOT_DIR)
    )

    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR)
    )

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None or frontend_proc.poll() is not None:
                break
    except KeyboardInterrupt:
        print("\n[DocMind] Shutting down dev servers...")
    finally:
        for p in [backend_proc, frontend_proc]:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                p.kill()


def main():
    os.chdir(str(ROOT_DIR))

    if "--dev" in sys.argv:
        run_dev_mode()
        return

    # 1. Build frontend if needed
    ensure_frontend_built()

    # 2. Check local LLM status
    from core.llm import get_model_info
    model_info = get_model_info()
    active_model = model_info.get("model_name", "None")
    is_ready = model_info.get("is_ready", False)
    models_available = model_info.get("available_models", [])

    model_summary = f"{active_model} (Ready)" if is_ready else "None detected (Run python download_model.py)"

    # 3. Print Welcome Banner
    banner = f"""
==================================================================
   [DocMind RAG + Second Brain] — Local Unified Server
==================================================================
   Privacy      :  100% Offline Local Inference (Zero API Keys)
   Active Model :  {model_summary}
   Found Models :  {len(models_available)} local GGUF model(s) in models/
   --------------------------------------------------------------
   Web App (UI) :  http://127.0.0.1:8000
   API Docs     :  http://127.0.0.1:8000/docs
   Health Check :  http://127.0.0.1:8000/health
==================================================================
   Serving React UI + FastAPI Backend on http://127.0.0.1:8000
   Press Ctrl+C to stop.
==================================================================
"""
    print(banner)

    # 4. Open browser
    open_browser_delayed("http://127.0.0.1:8000")

    # 5. Launch server
    import uvicorn
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
