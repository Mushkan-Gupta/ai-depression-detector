@echo off
setlocal EnableDelayedExpansion

:: Ensure we are working relative to the script's directory
cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║              MindEase — Launch Control Panel            ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

:: ── Step 1: Verify Python is installed ──────────────────────────────────────
echo [1/6] Verifying Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not available on your system PATH.
    echo         Please download and install Python from https://www.python.org/
    goto :FAIL
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do (
    echo        Found Python: %%v
)

:: ── Step 2-3: Verify and setup virtual environment ────────────────────────
echo [2/6] Verifying virtual environment...
set "VENV_DIR=ai-depression-risk-assessment\backend\venv"
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo        Virtual environment not found. Creating a new venv...
    echo        This may take a moment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment in "%VENV_DIR%".
        goto :FAIL
    )
    echo        [OK] Virtual environment created successfully.
) else (
    echo        [OK] Virtual environment exists.
)

:: ── Step 4: Activate virtual environment ──────────────────────────────────
echo [3/6] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    goto :FAIL
)
echo        [OK] Virtual environment activated.

:: ── Step 5: Install/Verify dependencies from requirements.txt ─────────────
echo [4/6] Verifying backend dependencies...
echo        Installing/updating required packages (this could take a minute)...
pip install -r ai-depression-risk-assessment\backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies.
    goto :FAIL
)
echo        [OK] Dependencies verified and up to date.

:: ── Step 6: Verify .env file exists ────────────────────────────────────────
echo [5/6] Verifying .env configuration...
set "ENV_FILE=ai-depression-risk-assessment\backend\.env"
if not exist "%ENV_FILE%" (
    echo        [WARNING] .env file not found.
    echo        Creating .env from .env.example...
    copy "ai-depression-risk-assessment\backend\.env.example" "%ENV_FILE%" >nul
    if errorlevel 1 (
        echo [ERROR] Failed to create .env file.
        goto :FAIL
    )
    echo        [IMPORTANT] .env file has been initialized.
    echo                    Please ensure your MongoDB Atlas credentials and
    echo                    Google Client IDs are correctly configured in:
    echo                    "%ENV_FILE%"
) else (
    echo        [OK] .env file verified.
)

:: ── Step 7-8: Start Backend and Frontend servers ──────────────────────────
echo [6/6] Launching MindEase servers...

echo        Starting Backend API...
start "MindEase Backend" cmd /k "cd ai-depression-risk-assessment\backend && call venv\Scripts\activate.bat && python app.py"
ping 127.0.0.1 -n 4 >nul

echo        Starting Frontend Web Server...
start "MindEase Frontend" cmd /k "python -m http.server 8000"
ping 127.0.0.1 -n 4 >nul

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                   SERVERS ACTIVE!                        ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo   Frontend: http://localhost:8000
echo   Backend:  http://127.0.0.1:5000
echo.
echo   Opening MindEase in your browser...
start http://localhost:8000

echo.
echo ─────────────────────────────────────────────────────────────
echo   Press any key to stop all servers and exit...
echo ─────────────────────────────────────────────────────────────
pause >nul

echo.
echo Stopping servers...
taskkill /FI "WINDOWTITLE eq MindEase Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MindEase Frontend*" /F >nul 2>&1
echo [OK] Servers stopped successfully.
goto :EOF

:FAIL
echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                     STARTUP FAILED!                      ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Please review the error messages above.
pause
exit /b 1
