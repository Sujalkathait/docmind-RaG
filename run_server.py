#!/usr/bin/env python3
"""
DocMind RAG + Second Brain — Unified Single-Port Server Launcher
100% Offline, Zero API Keys, Local GGUF LLM Execution.
Builds the React frontend (if needed) and serves both REST API and React UI on http://127.0.0.1:8000.
"""

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
        print("  [OK] React production bundle found in frontend/dist")


def open_browser_delayed(url: str, delay_seconds: float = 1.5):
    """Opens browser tab after server initializes."""
    def _open():
        time.sleep(delay_seconds)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()


def main():
    os.chdir(str(ROOT_DIR))

    # 1. Build frontend if needed
    ensure_frontend_built()

    # 2. Check local LLM status (Zero API keys verification)
    from core.llm import get_model_info
    model_info = get_model_info()
    active_model = model_info.get("model_name", "None")
    is_ready = model_info.get("is_ready", False)
    models_available = model_info.get("available_models", [])

    model_summary = f"{active_model} (Ready)" if is_ready else "None detected (Run python download_model.py)"

    # 3. Print Welcome Banner
    banner = f"""
==================================================================
   [DocMind RAG + Second Brain] — Unified Fullstack Server
==================================================================
   Privacy      :  100% Offline Local Inference (Zero API Keys)
   Active Model :  {model_summary}
   Found Models :  {len(models_available)} local GGUF model(s) in models/
   --------------------------------------------------------------
   Web App (UI) :  http://127.0.0.1:8000
   API Docs     :  http://127.0.0.1:8000/docs
   Health Check :  http://127.0.0.1:8000/health
==================================================================
   Serving both React Frontend + FastAPI REST Backend on Port 8000
   Press Ctrl+C to stop.
==================================================================
"""
    print(banner)

    # 4. Open browser in background
    open_browser_delayed("http://127.0.0.1:8000")

    # 5. Launch Uvicorn server
    import uvicorn
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
