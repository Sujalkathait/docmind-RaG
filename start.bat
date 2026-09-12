@echo off
setlocal
cd /d "%~dp0"
title DocMind RAG + Second Brain (Local Server)

echo ==================================================================
echo   DocMind RAG + Second Brain — Starting Unified Server
echo   100%% Private, Offline Local Inference (Zero API Keys)
echo ==================================================================

:: Detect Python executable
set "PYTHON_EXE="

if exist "C:\Users\LENOVO\AppData\Local\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=C:\Users\LENOVO\AppData\Local\Programs\Python\Python313\python.exe"
    goto :RunServer
)

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    goto :RunServer
)

:: Fallback to PATH python
set "PYTHON_EXE=python"

:RunServer
echo   Using Python: %PYTHON_EXE%
echo   Launching server on http://127.0.0.1:8000 ...
echo ==================================================================

"%PYTHON_EXE%" run.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server terminated with an error.
    pause
)
