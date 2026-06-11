# Configuration Guide

## Backend Configuration

### API Settings
The backend API runs on `http://127.0.0.1:5000` by default.

To change the port, edit `ai-depression-risk-assessment/backend/app.py`:
```python
app.run(host='127.0.0.1', port=5000, debug=True)
```

### Frontend API Connection
If you change the backend port, update `js/analyze.js`:
```javascript
const API_BASE_URL = 'http://127.0.0.1:5000';
```

## Model Configuration

### Training New Models
To retrain the depression detection model:

1. Prepare your dataset in `depression_dataset.csv`
2. Run the training script:
```bash
cd ai-depression-risk-assessment/backend
python train_model.py
```

This will generate:
- `depression_model.pkl` - The trained ML model
- `vectorizer.pkl` - The text vectorizer

### Model Parameters
Edit `train_model.py` to adjust:
- Training/test split ratio
- Model algorithm (LogisticRegression, RandomForest, etc.)
- Vectorizer parameters (max_features, ngram_range, etc.)

## Security Configuration

### Password Requirements
Current requirements (in `js/auth.js`):
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (@$!%*?&)

To modify, edit the regex in `isValidPassword()`:
```javascript
function isValidPassword(password) {
  return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$/.test(password);
}
```

### CORS Settings
CORS is enabled for all origins in development. For production, edit `app.py`:
```python
CORS(app, resources={r"/*": {"origins": "https://yourdomain.com"}})
```

## Theme Configuration

### Color Schemes
Edit CSS variables in `css/home.css` and `css/auth.css`:

```css
:root {
  --bg: #0a0e27;
  --text: #eaeaf0;
  --accent: #667eea;
  --mint: #48bb78;
}
```

### Default Theme
The app remembers the user's theme preference. To set a default, edit `js/theme.js`:
```javascript
// Set default to light theme
if (!localStorage.getItem("theme")) {
  localStorage.setItem("theme", "light");
  document.body.classList.add("light");
}
```

## Performance Optimization

### Model Loading
Models are loaded once at server startup. For large models, consider:
- Lazy loading
- Model caching
- Using lighter model formats (ONNX, TensorFlow Lite)

### Frontend Optimization
- Images are not used to reduce load time
- CSS animations use GPU acceleration
- Minimal JavaScript dependencies

## Environment Variables

Create a `.env` file for sensitive configuration:

```env
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here
MODEL_PATH=./depression_model.pkl
VECTORIZER_PATH=./vectorizer.pkl
```

Then load in `app.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Production Deployment

### Backend
1. Set `debug=False` in `app.py`
2. Use a production WSGI server (Gunicorn, uWSGI)
3. Set up HTTPS
4. Configure proper CORS origins
5. Add rate limiting
6. Implement proper authentication (JWT, OAuth)

### Frontend
1. Minify CSS and JavaScript
2. Use a CDN for static assets
3. Enable gzip compression
4. Implement proper error tracking
5. Add analytics

### Example Production Setup
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Monitoring

### Backend Logs
Flask logs are printed to console. For production:
```python
import logging
logging.basicConfig(filename='app.log', level=logging.INFO)
```

### API Monitoring
Add request logging in `app.py`:
```python
@app.before_request
def log_request():
    app.logger.info(f'{request.method} {request.path}')
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find process using port 5000
   lsof -i :5000  # Mac/Linux
   netstat -ano | findstr :5000  # Windows
   ```

2. **Model Loading Errors**
   - Check file paths are correct
   - Verify pickle files are not corrupted
   - Ensure scikit-learn version matches training version

3. **CORS Errors**
   - Verify flask-cors is installed
   - Check browser console for specific error
   - Try using a local server instead of file://

## Support

For issues or questions, check:
- [README.md](README.md) - Full documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide
- Console logs for error messages
