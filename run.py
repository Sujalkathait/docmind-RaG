import sys
import subprocess
import os

if __name__ == "__main__":
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    python_exe = sys.executable

    # Prefer virtual environment python if available
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        python_exe = venv_python

    print("=" * 60)
    print(" DOCMIND LOCAL RAG CHATBOT")
    print(f" Python Interpreter: {python_exe}")
    print("=" * 60)

    # Run streamlit via python -m streamlit run app.py
    cmd = [python_exe, "-m", "streamlit", "run", app_path]
    subprocess.run(cmd)
