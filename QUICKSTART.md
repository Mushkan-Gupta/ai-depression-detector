# Quick Start Guide

Get MindEase up and running in 3 simple steps!

## Step 1: Start the Backend Server

### On Windows:
```bash
cd ai-depression-risk-assessment/backend
start_server.bat
```

### On Mac/Linux:
```bash
cd ai-depression-risk-assessment/backend
chmod +x start_server.sh
./start_server.sh
```

### Or manually:
```bash
cd ai-depression-risk-assessment/backend
pip install -r requirements.txt
python app.py
```

You should see:
```
Starting AI Depression Detection API on port 5000...
✓ Model and vectorizer loaded successfully
* Running on http://127.0.0.1:5000
```

## Step 2: Open the Frontend

### Option A: Direct File Access
Simply open `index.html` in your web browser

### Option B: Local Server (Recommended)
```bash
# In the project root directory
python -m http.server 8000
```
Then navigate to: `http://localhost:8000`

## Step 3: Use the Application

1. **Create Account**: Click "Create account" and sign up
2. **Login**: Enter your credentials
3. **Write Journal**: Share your thoughts in the journal box
4. **Analyze**: Click "🔍 Analyze Journal" button
5. **View Results**: See your depression risk assessment

## Troubleshooting

### "Unable to connect to AI server"
- Make sure the backend server is running (Step 1)
- Check that it's running on port 5000
- Look for any error messages in the terminal

### "Model not loaded"
- Ensure `depression_model.pkl` and `vectorizer.pkl` exist in the backend folder
- If missing, run `train_model.py` to generate them

### CORS Errors
- Use a local server (Option B) instead of opening HTML directly
- Check that flask-cors is installed: `pip install flask-cors`

## Testing the API

You can test the backend directly:

```bash
curl -X POST http://127.0.0.1:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"journal": "I feel sad and lonely today"}'
```

Expected response:
```json
{
  "risk": "Moderate",
  "confidence": 0.85
}
```

## Need Help?

Check the full [README.md](README.md) for detailed documentation.

---

**Happy analyzing! 🌸**
