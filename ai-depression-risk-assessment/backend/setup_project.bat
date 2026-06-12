@echo off
setlocal EnableDelayedExpansion

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║           MindEase Backend — Project Setup               ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

:: ── Move to the directory where this script lives ─────────────────────────
cd /d "%~dp0"

:: ── Python check ──────────────────────────────────────────────────────────
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not on PATH.
    echo         Download from https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo        Found: %%v
echo.

:: ── Create venv if it does not exist ─────────────────────────────────────
echo [2/5] Setting up virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo        Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo        venv created successfully.
) else (
    echo        venv already exists — skipping creation.
)
echo.

:: ── Activate venv ─────────────────────────────────────────────────────────
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo        venv activated.
echo.

:: ── Install / upgrade packages ────────────────────────────────────────────
echo [4/5] Installing dependencies from requirements.txt...
pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)
echo.

:: ── Verify critical packages ──────────────────────────────────────────────
echo [5/5] Verifying critical packages...
python -c "import flask; print('        flask          ✓')"
python -c "import flask_jwt_extended; print('        flask_jwt_extended ✓')"
python -c "import pymongo; print('        pymongo        ✓')"
python -c "import sklearn; print('        scikit-learn   ✓')"
python -c "import numpy; print('        numpy          ✓')"
python -c "import dotenv; print('        python-dotenv  ✓')"
python -c "import email_validator; print('        email-validator✓')"
echo.

:: ── Check .env file ───────────────────────────────────────────────────────
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo           Copy .env.example to .env and fill in your credentials:
    echo           copy .env.example .env
    echo.
) else (
    echo [OK] .env file found.
    echo.
)

echo ╔══════════════════════════════════════════════════════════╗
echo ║  Setup complete! Run start_server.bat to launch the API  ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
pause
