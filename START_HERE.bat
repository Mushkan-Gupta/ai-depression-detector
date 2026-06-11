@echo off
echo ========================================
echo   MindEase - Starting Servers
echo ========================================
echo.

echo Starting Backend API...
start "MindEase Backend" cmd /k "cd ai-depression-risk-assessment\backend && python app.py"
timeout /t 3 /nobreak >nul

echo Starting Frontend Server...
start "MindEase Frontend" cmd /k "python -m http.server 8000"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   Servers Started!
echo ========================================
echo.
echo Frontend: http://localhost:8000
echo Backend:  http://127.0.0.1:5000
echo.
echo Opening browser...
start http://localhost:8000

echo.
echo Press any key to stop all servers...
pause >nul

echo.
echo Stopping servers...
taskkill /FI "WINDOWTITLE eq MindEase Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MindEase Frontend*" /F >nul 2>&1
echo Done!
