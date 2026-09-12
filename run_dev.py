#!/usr/bin/env python3
"""
DocMind RAG + Second Brain — Hot-Reloading Development Runner
Concurrently runs FastAPI backend on http://127.0.0.1:8000 and Vite dev server on http://localhost:5173.
"""

import sys
import subprocess
import time
import os
import signal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"


def main():
    print("=" * 65)
    print("  DocMind RAG + Second Brain — Hot-Reloading Dev Environment")
    print("  Backend API:  http://127.0.0.1:8000 (auto-reload)")
    print("  Vite React:   http://localhost:5173 (HMR enabled)")
    print("=" * 65)

    python_exec = sys.executable
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    # Start FastAPI backend
    backend_proc = subprocess.Popen(
        [python_exec, "-m", "uvicorn", "backend.api.main:app", "--reload", "--port", "8000"],
        cwd=str(ROOT_DIR)
    )

    # Start Vite frontend
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


if __name__ == "__main__":
    main()
