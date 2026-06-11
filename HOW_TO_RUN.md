# 🚀 How to Run MindEase

## Method 1: Double-Click (Easiest) ⭐

**Windows:**
1. Double-click `START_HERE.bat`
2. Browser will open automatically!

## Method 2: Python Script

1. Open terminal in VS Code (Ctrl + `)
2. Run:
```bash
python start_mindease.py
```

## Method 3: VS Code Tasks

1. Press `Ctrl + Shift + P`
2. Type: "Tasks: Run Task"
3. Select: "Start MindEase (All Servers)"

## Method 4: Manual Commands

**Terminal 1 - Backend:**
```bash
cd ai-depression-risk-assessment/backend
python app.py
```

**Terminal 2 - Frontend:**
```bash
python -m http.server 8000
```

Then open: http://localhost:8000

## What You'll See

- Backend API: http://127.0.0.1:5000
- Frontend: http://localhost:8000

## Troubleshooting

**Port already in use?**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Python not found?**
- Make sure Python is installed
- Try `python3` instead of `python`

---

**Recommended:** Use Method 1 (START_HERE.bat) - it's the easiest!
