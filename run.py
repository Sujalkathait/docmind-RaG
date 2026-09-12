from __future__ import annotations

import sys
import subprocess
import os


if __name__ == "__main__":
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    python_exe = sys.executable

    # Prefer virtual environment python if available and functional
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        try:
            res = subprocess.run([venv_python, "--version"], capture_output=True, timeout=3)
            if res.returncode == 0:
                python_exe = venv_python
        except Exception:
            pass

    print("=" * 60)
    print(" DOCMIND RAG + SECOND BRAIN LEARNING ASSISTANT")
    print(f" Python Interpreter: {python_exe}")
    print("=" * 60)

    # Run streamlit via python -m streamlit run app.py
    cmd = [python_exe, "-m", "streamlit", "run", app_path]
    subprocess.run(cmd)

