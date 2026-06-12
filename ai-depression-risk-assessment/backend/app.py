from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request
import pickle
import os
from datetime import datetime, timezone

from config import Config
import db as _db
from db import init_db

app = Flask(__name__)
app.config.from_object(Config)

# ── CORS ────────────────────────────────────────────────────────────────────
CORS(app, origins=Config.ALLOWED_ORIGINS)

# ── JWT ─────────────────────────────────────────────────────────────────────
jwt = JWTManager(app)

# ── MongoDB ─────────────────────────────────────────────────────────────────
init_db(app)

# ── Blueprints ───────────────────────────────────────────────────────────────
from routes.auth_routes import auth_bp
app.register_blueprint(auth_bp)

from routes.history_routes import history_bp
app.register_blueprint(history_bp)

# ── Model Loading ──────────────────────────────────────────────────────────
model = None
vectorizer = None

try:
    base_dir        = os.path.dirname(os.path.abspath(__file__))
    model_path      = os.path.join(base_dir, "depression_model.pkl")
    vectorizer_path = os.path.join(base_dir, "vectorizer.pkl")

    if os.path.exists(model_path) and os.path.exists(vectorizer_path):
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        with open(vectorizer_path, "rb") as f:
            vectorizer = pickle.load(f)
        print("[OK] Model loaded successfully")
    else:
        print("[WARNING] Model files not found. Using keyword classification only.")
except Exception as e:
    print(f"[ERROR] Error loading model: {e}")


# ── Keyword Lexicons ───────────────────────────────────────────────────────

# HIGH severity: clear crisis / suicidality signals → always forces High
HIGH_RISK_KEYWORDS = [
    'suicide', 'kill myself', 'end it all', 'want to die', 'better off dead',
    'no reason to live', 'self harm', 'hurt myself', 'ending my life',
    'taking my life', 'end my life', 'overdose', 'not want to be alive',
    'wishing i was dead', 'thinking about death', 'no longer want to live',
    'not wanting to exist', 'do not want to live', 'do not want to exist',
    "don't want to live", "don't want to exist", 'want to disappear forever',
    'searching for methods', 'searching online for', 'looking up how to',
    'not worth living', 'life is not worth', 'no longer worth living',
]

# MODERATE severity: strong depression indicators but not crisis-level
MODERATE_RISK_KEYWORDS = [
    'depressed', 'depression', 'severely depressed', 'suicidal thoughts',
    'panic attack', 'no will to live', 'completely exhausted and numb',
    'numb inside', 'empty inside', 'hate myself', 'feel like a burden',
    'nobody cares', 'all alone', 'disconnected from', 'meaningless',
    "don't want to wake up", 'feel like disappearing', 'lost all hope',
    'no motivation whatsoever', 'crying all the time', 'deeply depressed',
]

# MILD signals: common stress/sadness words that need to accumulate to matter
MILD_NEGATIVE_KEYWORDS = [
    'sad', 'lonely', 'anxious', 'anxiety', 'stressed', 'stress', 'overwhelmed',
    'tired', 'exhausted', 'struggling', 'unmotivated', 'hard time', 'difficult',
    'worried', 'fear', 'insomnia', 'can\'t sleep', 'low energy', 'withdrawn',
    'down', 'crying', 'cried', 'numb', 'flat', 'irritable', 'frustrated',
    'burned out', 'burnt out', 'lost', 'confused', 'empty', 'grief', 'grieving',
    'loss', 'heartbroken', 'hopeless', 'worthless', 'give up', 'no point',
    'no energy', 'not okay', 'falling apart', 'running on empty', 'no motivation',
    'isolating', 'withdrawing', 'can\'t function', 'panic', 'dark days',
    'really dark', 'very dark', 'bad days', 'dark place', 'heavy mood',
    'miserable', 'dread', 'dreading', 'dreaded', 'guilt', 'guilty',
    'shame', 'ashamed', 'disconnected', 'detached', 'isolated', 'avoid',
]

# POSITIVE signals: actively reduce depression probability
POSITIVE_KEYWORDS = [
    'happy', 'happiness', 'grateful', 'gratitude', 'excited', 'joy', 'joyful',
    'peaceful', 'content', 'hopeful', 'motivated', 'thankful', 'loved', 'love',
    'optimistic', 'wonderful', 'great day', 'feeling good', 'blessed', 'proud',
    'energetic', 'rested', 'calm', 'connected', 'supported', 'inspired',
    'fulfilled', 'relieved', 'laughter', 'laugh', 'smile', 'smiling',
    'looking forward', 'positive', 'thriving', 'growing',
]


def keyword_classify(text: str):
    """
    Primary classifier using an evidence-weighted keyword scoring system.
    Returns (risk: str, confidence: float, evidence: dict)
    
    Architecture:
    - Crisis keywords → High (hard rule)
    - Weighted score from strong/mild negatives minus positive counter-evidence
    - Score thresholds produce Low / Moderate / High
    """
    lower = text.lower()
    word_count = max(len(text.split()), 1)

    high_hits     = [kw for kw in HIGH_RISK_KEYWORDS     if kw in lower]
    moderate_hits = [kw for kw in MODERATE_RISK_KEYWORDS if kw in lower]
    mild_hits     = [kw for kw in MILD_NEGATIVE_KEYWORDS if kw in lower]
    positive_hits = [kw for kw in POSITIVE_KEYWORDS      if kw in lower]

    # Crisis: immediate High
    if high_hits:
        n = len(high_hits)
        confidence = min(0.95, 0.72 + n * 0.08)
        return "High", round(confidence, 3), {
            "crisis": high_hits, "moderate": moderate_hits,
            "mild": mild_hits, "positive": positive_hits
        }

    # Score = strong negatives + fractional mild negatives - positive counter-evidence
    # Mild negatives are capped at 0.5 weight each to require more to reach Moderate
    # Positive hits actively subtract
    neg_score = (len(moderate_hits) * 0.30
                 + min(len(mild_hits), 12) * 0.10   # cap mild contribution
                 - len(positive_hits) * 0.08)        # gentler positive dampening

    # Normalise slightly by text length to prevent short texts from over-scoring
    # (journal entries should be long — if short, cap the score)
    if word_count < 50:
        neg_score *= 0.7

    neg_score = max(neg_score, 0.0)

    # Map score to risk level
    if neg_score >= 1.0:
        # Multiple strong indicators
        confidence = min(0.92, 0.62 + neg_score * 0.06)
        return "Moderate", round(confidence, 3), {
            "crisis": high_hits, "moderate": moderate_hits,
            "mild": mild_hits, "positive": positive_hits
        }
    elif neg_score >= 0.20:   # Lowered from 0.30 to catch grief/anxiety entries
        confidence = min(0.80, 0.45 + neg_score * 0.15)
        return "Moderate", round(confidence, 3), {
            "crisis": high_hits, "moderate": moderate_hits,
            "mild": mild_hits, "positive": positive_hits
        }
    else:
        # Positive score or very few negatives
        pos_score  = len(positive_hits) * 0.10
        confidence = min(0.88, 0.45 + pos_score * 0.12)
        return "Low", round(confidence, 3), {
            "crisis": high_hits, "moderate": moderate_hits,
            "mild": mild_hits, "positive": positive_hits
        }


# ── Routes ─────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return {
        "status":       "running",
        "message":      "MindEase AI Depression Detection API",
        "model_loaded": model is not None
    }


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(force=True)

        if not data or "journal" not in data:
            return {"error": "No journal text provided"}, 400

        journal = data["journal"]
        if not journal.strip():
            return {"error": "Journal text is empty"}, 400

        # ── Primary: keyword-based classification ──────────────────
        kw_risk, kw_confidence, evidence = keyword_classify(journal)

        # ── Secondary: ML model (used only for borderline cases) ────
        ml_dep_prob   = None

        if model is not None and vectorizer is not None:
            try:
                vec = vectorizer.transform([journal])
                if hasattr(model, "predict_proba"):
                    proba       = model.predict_proba(vec)[0]
                    ml_dep_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])
                else:
                    raw = model.predict(vec)[0]
                    ml_dep_prob = 1.0 if raw == 1 else 0.0
            except Exception as e:
                print(f"[WARN] ML failed: {e}")
                ml_dep_prob = None

        # ── Blending strategy ──────────────────────────────────────
        # The ML model was trained on short Reddit posts, not long journal entries.
        # On long narrative text, it tends to output very high depression scores
        # regardless of actual sentiment (probability >0.90 for almost all).
        # 
        # Blending rules:
        #  1. Keyword classification is ALWAYS the base result.
        #  2. ML can only DOWNGRADE (Low/Moderate → lower confidence), never upgrade.
        #  3. Exception: if keyword says Low but there are mild negative words AND
        #     ML also fires, treat with caution and output Low with lower confidence.

        risk       = kw_risk
        confidence = kw_confidence

        if ml_dep_prob is not None:
            if kw_risk == "Moderate" and ml_dep_prob < 0.10:
                # ML strongly disagrees with Moderate keyword classification.
                # Downgrade to Low — entry likely uses neutral/formal language.
                risk       = "Low"
                confidence = round(max(0.38, kw_confidence - 0.15), 3)
            # (All other cases: trust keyword analysis fully)

        print(f"[PREDICT] risk={risk}  kw_conf={kw_confidence}  ml_dep_prob={ml_dep_prob}  words={len(journal.split())}")

        # ── Optional: save to MongoDB if JWT token present ─────────
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
        except Exception:
            identity = None

        if identity:
            try:
                _db.journal_entries_collection.insert_one({
                    "user_id":    identity,   # identity is the user_id string (sub claim)
                    "journal":    journal,
                    "risk":       risk,
                    "confidence": confidence,
                    "created_at": datetime.now(timezone.utc),
                })
            except Exception as db_err:
                print(f"[WARN] Failed to save prediction history: {db_err}")

        return jsonify({"risk": risk, "confidence": confidence})

    except Exception as e:
        print(f"[ERROR] {e}")
        return {"error": str(e)}, 500


if __name__ == "__main__":
    print("Starting MindEase API on http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=Config.PORT, debug=Config.DEBUG)