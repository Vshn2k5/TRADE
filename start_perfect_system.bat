@echo off
echo ============================================================
echo APEX INDIA - Starting Command Center (Free Setup)
echo ============================================================

:: Check if venv exists
if not exist venv (
    echo [ERROR] Virtual environment not found. Please run installation first.
    pause
    exit /b
)

:: Start FastAPI Backend in a new window
echo [SERVER] Launching Premium Dashboard on http://localhost:8000 ...
start "APEX Dashboard" cmd /c ".\venv\Scripts\python.exe -m uvicorn apex_india.server.app:app --host 0.0.0.0 --port 8000"

:: Wait a bit for server to warm up
timeout /t 3 /nobreak > nul

:: Start Trading Scheduler
echo [SYSTEM] Starting Strategy Orchestrator (Paper Mode Default) ...
.\venv\Scripts\python.exe scheduler.py --mode paper

pause
