#!/usr/bin/env python3
"""
MindEase Server Launcher
Run this script to start both frontend and backend servers
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def print_banner():
    print("\n" + "="*50)
    print("  MindEase - AI Mental Health Support")
    print("="*50 + "\n")

def start_backend():
    """Start the Flask backend server"""
    print("[INFO] Starting Backend API Server...")
    backend_path = Path("ai-depression-risk-assessment/backend")
    
    if not backend_path.exists():
        print("[ERROR] Backend directory not found!")
        return None
    
    try:
        backend_process = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=str(backend_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("[OK] Backend server starting on http://127.0.0.1:5000")
        return backend_process
    except Exception as e:
        print(f"[ERROR] Failed to start backend: {e}")
        return None

def start_frontend():
    """Start the frontend HTTP server"""
    print("[INFO] Starting Frontend Web Server...")
    
    try:
        frontend_process = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("[OK] Frontend server starting on http://localhost:8000")
        return frontend_process
    except Exception as e:
        print(f"[ERROR] Failed to start frontend: {e}")
        return None

def main():
    print_banner()
    
    # Start backend
    backend = start_backend()
    if not backend:
        print("\n[ERROR] Failed to start backend server")
        sys.exit(1)
    
    time.sleep(2)  # Wait for backend to initialize
    
    # Start frontend
    frontend = start_frontend()
    if not frontend:
        print("\n[ERROR] Failed to start frontend server")
        backend.terminate()
        sys.exit(1)
    
    time.sleep(2)  # Wait for frontend to initialize
    
    # Print success message
    print("\n" + "="*50)
    print("  [OK] ALL SERVERS RUNNING!")
    print("="*50)
    print("\nFrontend: http://localhost:8000")
    print("Backend:  http://127.0.0.1:5000")
    print("\n" + "="*50)
    print("  Opening browser...")
    print("="*50 + "\n")
    
    # Open browser
    try:
        webbrowser.open("http://localhost:8000")
        print("[OK] Browser opened!")
    except:
        print("[WARNING] Please manually open: http://localhost:8000")
    
    print("\n" + "="*50)
    print("  Press Ctrl+C to stop all servers")
    print("="*50 + "\n")
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Stopping servers...")
        backend.terminate()
        frontend.terminate()
        print("[OK] All servers stopped. Goodbye!")

if __name__ == "__main__":
    main()
