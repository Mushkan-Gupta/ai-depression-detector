#!/bin/bash

echo "========================================"
echo "  MindEase AI Backend Server"
echo "========================================"
echo ""
echo "Checking Python installation..."
python3 --version
echo ""
echo "Installing dependencies..."
pip3 install -r requirements.txt
echo ""
echo "Starting Flask server..."
echo "Server will run on http://127.0.0.1:5000"
echo "Press Ctrl+C to stop the server"
echo ""
python3 app.py
