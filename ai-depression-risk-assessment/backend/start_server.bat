@echo off
setlocal EnableDelayedExpansion

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║           MindEase AI Backend — Starting Server          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

:: ── Move to the directory where this script lives ─────────────────────────
cd /d "%~dp0"

:: ── Check venv exists ─────────────────────────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo         Run setup_project.bat first to create it.
    echo.
    pause
    exit /b 1
)

:: ── Activate venv ─────────────────────────────────────────────────────────
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated.

:: ── Check .env file ───────────────────────────────────────────────────────
if not exist ".env" (
    echo.
    echo [ERROR] .env file not found!
    echo         Copy .env.example to .env and fill in your credentials.
    echo         Run: copy .env.example .env
    echo.
    pause
    exit /b 1
)
echo [OK] .env file found.

:: ── Install any missing packages (silent) ─────────────────────────────────
echo [..] Checking dependencies...
pip install -r requirements.txt --quiet
echo [OK] Dependencies verified.
echo.

:: ── Launch Flask server ───────────────────────────────────────────────────
echo [..] Starting MindEase API on http://127.0.0.1:5000
echo      Press Ctrl+C to stop the server.
echo.
python app.py

:: ── On exit ───────────────────────────────────────────────────────────────
echo.
echo Server stopped.
pause
