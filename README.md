# MindEase - AI Depression Risk Assessment

A professional mental health support application with AI-powered depression risk assessment, secure authentication, and a peer support network.

## 🌟 Features

- **🤖 AI-Powered Depression Risk Assessment**
  - Analyzes journal entries in real-time to detect low, moderate, or high risk of depression.
  - Returns a calibrated confidence score for every prediction.
  - Automated **Crisis Escalation**: Instantly detects severe crisis keywords and provides immediate, prominent safety resources.

- **🤝 Peer Support Network**
  - **Peer Connect**: Find and connect with empathetic listeners anonymously.
  - **Real-Time Peer Chat**: Secure messaging interface for peer-to-peer conversations with built-in safety banners.

- **🔐 Secure User Accounts & History**
  - Complete authentication system with email/password (bcrypt hashing) and **Google OAuth** login.
  - **MongoDB Integration**: Securely persists user profiles, journal history, and peer connections.

- **🎨 Modern, Professional UI**
  - Responsive design with glassmorphism effects and smooth animations.
  - Built-in Dark/Light theme toggling.
  - Color-coded risk level badges and intuitive dashboards.

## 🛠 Tech Stack

### Frontend
- **Core:** HTML5, CSS3, Vanilla JavaScript
- **Styling:** Custom CSS with Glassmorphism, Google Fonts (Poppins)
- **Integration:** Real-time DOM updates, Fetch API for backend communication

### Backend
- **Framework:** Python, Flask, Flask-CORS
- **Database:** MongoDB Atlas (PyMongo)
- **Authentication:** Flask-JWT-Extended, Google Auth library, Werkzeug security
- **Machine Learning:** scikit-learn (Logistic Regression, TfidfVectorizer), NumPy, Pandas, Pickle (Serialization)

## 📁 Project Structure

```
MindEase/
├── auth.html                 # Login, Registration & Google Auth page
├── index.html                # Main Dashboard, Journal Entry & History
├── peer-connect.html         # Peer Support Matching Portal
├── peer-chat.html            # Real-Time Peer Conversation Interface
├── css/                      # Stylesheets (auth.css, home.css, dashboard.css)
├── js/                       # Client-side logic (analyze.js, auth.js, peer-*.js)
└── ai-depression-risk-assessment/
    └── backend/
        ├── app.py                   # Main Flask API Server & ML Prediction endpoint
        ├── config.py                # Environment configuration
        ├── db.py                    # MongoDB connection management
        ├── train_model.py           # ML Model training script
        ├── depression_model.pkl     # Trained ML Logistic Regression model
        ├── vectorizer.pkl           # Trained TF-IDF Vectorizer
        ├── depression_dataset.csv   # Training dataset (Reddit corpus)
        ├── requirements.txt         # Python dependencies
        ├── constants/
        │   └── keywords.py          # Crisis safety keyword definitions
        ├── routes/                  # API Routers (auth, history, peer)
        ├── utils/
        │   └── crisis_check.py      # Automated crisis escalation logic
        └── tests/                   # Pytest automated testing suite
```

## 🚀 Setup Instructions

### Prerequisites
- Python 3.14+
- Modern web browser
- MongoDB Atlas account (or local MongoDB)
- Node.js (Optional, for local HTTP server)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd ai-depression-risk-assessment/backend
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

3. Install required Python packages:
```bash
pip install -r requirements.txt
```

4. Configure Environment Variables:
Copy `.env.example` to `.env` and fill in your MongoDB URI and JWT Secret Key.
```bash
cp .env.example .env
```

5. Start the Flask server:
```bash
python app.py
```
*The server will start on `http://127.0.0.1:5000`*

### Frontend Setup

1. Serve the frontend files using a local HTTP server from the root directory:
```bash
# Using Python's built-in server
python -m http.server 8000
```

2. Navigate to `http://localhost:8000/auth.html` in your browser.

## 📝 API Endpoints (Core)

- `GET /` : Health check and model loading status.
- `POST /predict` : Analyzes journal text and returns depression risk assessment (`risk` and `confidence`), along with crisis escalation flags.
- `POST /api/auth/register` : User registration.
- `POST /api/auth/login` : User login.
- `POST /api/auth/google` : Google OAuth login.
- `GET /api/history` : Retrieve user's journal history.
- `POST /api/peer/connect` : Send a peer connection request.

## 🔒 Security Notes

- Passwords are hashed using bcrypt before storage.
- All API routes (except auth and predict) are protected using JWT (JSON Web Tokens).
- Real-time crisis detection prevents high-risk text from being silently processed, instantly alerting the user with emergency resources.
- CORS is restricted to allowed origins in production.

## 📈 Future Enhancements

- Mobile app version (React Native / Flutter).
- Multi-language support for risk assessment.
- Mood tracking calendar visualizations.
- Progress tracking analytics over time.

## 📜 License

© 2026 MindEase · AI Mental Health Support

---

**Note**: This application is for educational and supportive purposes. It does not replace professional medical advice. Always consult healthcare professionals for mental health concerns.
