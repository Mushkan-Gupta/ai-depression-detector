@echo off
echo ========================================
echo   MindEase AI Backend Server
echo ========================================
echo.
echo Checking Python installation...
python --version
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Starting Flask server...
echo Server will run on http://127.0.0.1:5000
echo Press Ctrl+C to stop the server
echo.
python app.py
pause
