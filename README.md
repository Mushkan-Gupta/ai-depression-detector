# MindEase - AI Depression Risk Assessment

A professional mental health support application with AI-powered depression risk assessment.

## Features

- 🎨 Modern, professional UI with smooth animations
- 🤖 AI-powered depression risk assessment
- 🔐 Secure authentication system
- 🌓 Dark/Light theme support
- 💬 Interactive chat interface
- 📝 Journal analysis with confidence scores

## Tech Stack

### Frontend
- HTML5, CSS3, JavaScript
- Responsive design with glassmorphism effects
- Real-time API integration

### Backend
- Python Flask
- Machine Learning (scikit-learn)
- Pickle for model serialization
- CORS enabled for cross-origin requests

## Setup Instructions

### Prerequisites
- Python 3.7+
- Modern web browser
- pip (Python package manager)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd ai-depression-risk-assessment/backend
```

2. Install required Python packages:
```bash
pip install flask flask-cors numpy scikit-learn
```

3. Start the Flask server:
```bash
python app.py
```

The server will start on `http://127.0.0.1:5000`

### Frontend Setup

1. Open `index.html` in your web browser, or use a local server:
```bash
# Using Python's built-in server
python -m http.server 8000
```

2. Navigate to `http://localhost:8000` in your browser

## Usage

1. **Login/Signup**: Create an account or login with existing credentials
2. **Journal Entry**: Write your thoughts in the journal textarea
3. **AI Analysis**: Click "Analyze Journal" to get depression risk assessment
4. **View Results**: See risk level (Low/Moderate/High) with confidence score

## API Endpoints

### GET /
Returns API status and model loading state

### POST /predict
Analyzes journal text and returns depression risk assessment

**Request Body:**
```json
{
  "journal": "Your journal text here..."
}
```

**Response:**
```json
{
  "risk": "Low|Moderate|High",
  "confidence": 0.85
}
```

## Project Structure

```
.
├── index.html              # Login/Signup page
├── home.html              # Main application page
├── css/
│   ├── auth.css          # Authentication page styles
│   └── home.css          # Home page styles
├── js/
│   ├── auth.js           # Authentication logic
│   ├── analyze.js        # AI analysis integration
│   ├── chat.js           # Chat functionality
│   └── theme.js          # Theme switching
└── ai-depression-risk-assessment/
    └── backend/
        ├── app.py                    # Flask API server
        ├── predict.py                # Prediction logic
        ├── train_model.py            # Model training script
        ├── depression_model.pkl      # Trained ML model
        ├── vectorizer.pkl            # Text vectorizer
        └── depression_dataset.csv    # Training dataset
```

## Security Notes

- Passwords are validated for strength (uppercase, lowercase, number, symbol)
- Email validation is performed
- CORS is enabled for local development
- For production, implement proper authentication and HTTPS

## Troubleshooting

### Backend Connection Error
- Ensure Flask server is running on port 5000
- Check console for CORS errors
- Verify `API_BASE_URL` in `js/analyze.js` matches your backend URL

### Model Loading Error
- Ensure `depression_model.pkl` and `vectorizer.pkl` exist in backend directory
- Run `train_model.py` if models are missing

## Future Enhancements

- Database integration for user data persistence
- Real-time chat with AI therapist
- Progress tracking and analytics
- Mobile app version
- Multi-language support

## License

© 2026 MindEase · AI Mental Health Support

---

**Note**: This application is for educational purposes. Always consult healthcare professionals for mental health concerns.
