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

from routes.peer_routes import peer_bp
app.register_blueprint(peer_bp)

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
from constants.keywords import (
    HIGH_RISK_KEYWORDS, 
    MODERATE_RISK_KEYWORDS, 
    MILD_NEGATIVE_KEYWORDS, 
    POSITIVE_KEYWORDS, 
    INDIRECT_IDEATION_PHRASES, 
    CONTEXT_GATED_PHRASES
)


def keyword_classify(text: str):
    """
    Primary classifier using an evidence-weighted keyword scoring system.
    Returns (risk: str, confidence: float, evidence: dict, neg_score: float)
    
    Architecture:
    - Crisis keywords → High (hard rule, unchanged)
    - Indirect ideation phrases → AT MINIMUM Moderate (safety floor, see
      INDIRECT_IDEATION_PHRASES above for rationale)
    - Weighted score from strong/mild negatives minus positive counter-evidence
    - Score thresholds produce Low / Moderate / High
    """
    lower = text.lower()
    word_count = max(len(text.split()), 1)

    high_hits     = [kw for kw in HIGH_RISK_KEYWORDS        if kw in lower]
    indirect_hits = [kw for kw in INDIRECT_IDEATION_PHRASES if kw in lower]
    moderate_hits = [kw for kw in MODERATE_RISK_KEYWORDS    if kw in lower]
    mild_hits     = [kw for kw in MILD_NEGATIVE_KEYWORDS    if kw in lower]
    positive_hits = [kw for kw in POSITIVE_KEYWORDS         if kw in lower]

    # Crisis: immediate High (unchanged — do NOT modify)
    if high_hits:
        n = len(high_hits)
        confidence = min(0.95, 0.72 + n * 0.08)
        return "High", round(confidence, 3), {
            "crisis": high_hits, "indirect": indirect_hits,
            "moderate": moderate_hits, "mild": mild_hits, "positive": positive_hits,
            "gated_indirect": [], "ungated_indirect": indirect_hits,
            "gated_passes_kw": True,
        }, 2.0  # arbitrary high score for crisis

    # Score = strong negatives + fractional mild negatives - positive counter-evidence
    # Mild negatives are capped at 0.5 weight each to require more to reach Moderate
    # Positive hits actively subtract
    neg_score = (len(moderate_hits) * 0.30
                 + min(len(mild_hits), 12) * 0.10   # cap mild contribution
                 - len(positive_hits) * 0.08)        # gentler positive dampening

    # (Removed length penalty since we now blend with the ML model gracefully)

    neg_score = max(neg_score, 0.0)

    # ── Indirect ideation floor ────────────────────────────────────────────
    # Separate indirect hits into two buckets:
    #   - ungated: specific enough to enforce the floor unconditionally
    #   - gated:   short/ambiguous phrases that need corroboration (see
    #              CONTEXT_GATED_PHRASES for the rationale)
    ungated_indirect = [p for p in indirect_hits if p not in CONTEXT_GATED_PHRASES]
    gated_indirect   = [p for p in indirect_hits if p in CONTEXT_GATED_PHRASES]

    has_indirect = len(indirect_hits) > 0

    # Context gate for gated phrases: check routes (a) and (c) here.
    # Route (b) — ml_dep_prob — is checked in the /predict route where
    # the ML probability is available.
    #
    # Route (a): any moderate or mild keyword hit that is NOT a substring
    # of an already-matched gated phrase. E.g. "tired" is inside
    # "tired of fighting", so it does NOT count as independent evidence.
    def _is_independent(kw, gated_phrases):
        """Return True if kw is not a substring of any matched gated phrase."""
        return not any(kw in gp for gp in gated_phrases)

    independent_moderate = [kw for kw in moderate_hits if _is_independent(kw, gated_indirect)]
    independent_mild     = [kw for kw in mild_hits     if _is_independent(kw, gated_indirect)]
    has_kw_corroboration = len(independent_moderate) > 0 or len(independent_mild) > 0
    # Route (c): more than one *distinct* indirect phrase matched
    has_multi_indirect   = len(indirect_hits) >= 2 and len(set(indirect_hits)) >= 2

    gated_passes = has_kw_corroboration or has_multi_indirect

    # Apply the neg_score floor only for:
    #   1. Any ungated (specific) indirect phrase, OR
    #   2. A gated phrase whose context gate passes via routes (a)/(c)
    # The flag is_gated_only tells the predict route whether to apply route (b)
    if ungated_indirect or (gated_indirect and gated_passes):
        neg_score = max(neg_score, 0.55)   # 0.55 → sigmoid(4*(0.55-0.5)) ≈ 0.55, well into Moderate
    # If only gated phrases matched and the keyword gate didn't pass,
    # we defer the decision to the predict route (which can check ml_dep_prob).

    # Map score to risk level
    if neg_score >= 1.0:
        # Multiple strong indicators
        confidence = min(0.92, 0.62 + neg_score * 0.06)
        return "Moderate", round(confidence, 3), {
            "crisis": high_hits, "indirect": indirect_hits,
            "moderate": moderate_hits, "mild": mild_hits, "positive": positive_hits,
            "gated_indirect": gated_indirect, "ungated_indirect": ungated_indirect,
            "gated_passes_kw": gated_passes,
        }, neg_score
    elif neg_score >= 0.20:   # Lowered from 0.30 to catch grief/anxiety entries
        confidence = min(0.80, 0.45 + neg_score * 0.15)
        return "Moderate", round(confidence, 3), {
            "crisis": high_hits, "indirect": indirect_hits,
            "moderate": moderate_hits, "mild": mild_hits, "positive": positive_hits,
            "gated_indirect": gated_indirect, "ungated_indirect": ungated_indirect,
            "gated_passes_kw": gated_passes,
        }, neg_score
    else:
        # Positive score or very few negatives
        pos_score  = len(positive_hits) * 0.10
        confidence = min(0.88, 0.45 + pos_score * 0.12)
        return "Low", round(confidence, 3), {
            "crisis": high_hits, "indirect": indirect_hits,
            "moderate": moderate_hits, "mild": mild_hits, "positive": positive_hits,
            "gated_indirect": gated_indirect, "ungated_indirect": ungated_indirect,
            "gated_passes_kw": gated_passes,
        }, neg_score


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
        kw_risk, kw_confidence, evidence, neg_score = keyword_classify(journal)

        # ── Secondary: ML model ─────────────────────────────────────
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
        import math
        
        # 1. HARD CONSTRAINT: Crisis keywords are an unoverridable override
        if len(evidence["crisis"]) > 0:
            risk = "High"
            confidence = kw_confidence
            print(f"[PREDICT] CRISIS OVERRIDE: risk={risk} conf={confidence}")
        else:
            if ml_dep_prob is not None:
                # 2. Normalize neg_score via a sigmoid function to keep it between 0 and 1
                # Center it around 0.5 so a neg_score of 0.5 evaluates to ~0.5
                norm_neg = 1 / (1 + math.exp(-4 * (neg_score - 0.5)))
                
                # 3. Blend the signals using tuned weights (60% KW / 40% ML)
                W_KW = 0.6
                W_ML = 0.4
                blended_score = (W_KW * norm_neg) + (W_ML * ml_dep_prob)
                
                # 4. Map blended score to risk thresholds
                if blended_score >= 0.65:
                    risk = "High"
                elif blended_score >= 0.32:
                    risk = "Moderate"
                else:
                    risk = "Low"
                    
                confidence = round(min(0.95, 0.4 + blended_score * 0.55), 3)

                # 5. SAFETY FLOOR A — Indirect ideation detected
                # CONTEXT-GATED: If only gated (short/ambiguous) phrases matched
                # and keyword corroboration didn't pass, we check route (b) here:
                # ml_dep_prob >= 0.4 means the model sees *some* depression signal.
                # Threshold rationale: 0.4 is the lower edge of the existing
                # "uncertain band" (floor B below). Below 0.4 the model is
                # reasonably confident the text is NOT depressive.
                gated_only = (len(evidence.get("gated_indirect", [])) > 0
                              and len(evidence.get("ungated_indirect", [])) == 0
                              and not evidence.get("gated_passes_kw", False))

                if len(evidence["indirect"]) > 0 and risk == "Low":
                    if gated_only:
                        # Route (b): ML corroboration check
                        if ml_dep_prob >= 0.4:
                            risk = "Moderate"
                            confidence = max(confidence, 0.60)
                            print(f"[PREDICT] INDIRECT IDEATION FLOOR applied (gated, ML corroboration): "
                                  f"phrases={evidence['indirect']} ml_prob={ml_dep_prob:.3f}")
                        else:
                            # All three routes failed — no corroboration at all.
                            # Let the entry stay Low.  This is what prevents the
                            # false-positive on everyday uses of short phrases.
                            print(f"[PREDICT] CONTEXT GATE BLOCKED indirect floor: "
                                  f"gated_phrases={evidence['gated_indirect']} "
                                  f"ml_prob={ml_dep_prob:.3f} (below 0.4, no KW corroboration)")
                    else:
                        # Ungated phrases or keyword-corroborated gated phrases
                        risk = "Moderate"
                        confidence = max(confidence, 0.60)
                        print(f"[PREDICT] INDIRECT IDEATION FLOOR applied: phrases={evidence['indirect']}")

                # 6. SAFETY FLOOR B — Low ML confidence (uncertain band)
                # When the ML model's depression probability is in the 0.40–0.60 range
                # the model itself is essentially at chance. Defaulting to "Low" in
                # this uncertain band is a false-reassurance risk. We instead floor
                # the output to "Moderate" and ensure crisis resources are displayed.
                # Threshold rationale: <0.40 = model is reasonably confident non-dep;
                #                     >0.60 = model is reasonably confident dep;
                #                     0.40–0.60 = model is uncertain → treat cautiously.
                # FIX: Require neg_score >= 0.10 (at least one mild keyword baseline) 
                # so short positive/neutral text doesn't arbitrarily trigger the floor.
                if 0.40 <= ml_dep_prob <= 0.60 and risk == "Low" and neg_score >= 0.10:
                    risk = "Moderate"
                    confidence = max(confidence, 0.55)
                    print(f"[PREDICT] LOW-CONFIDENCE FLOOR applied (neg_score={neg_score:.3f}): ml_prob={ml_dep_prob:.3f} in uncertain band [0.40, 0.60]")


                print(f"[PREDICT] BLEND: neg_score={neg_score:.3f} norm_neg={norm_neg:.3f} ml_prob={ml_dep_prob:.3f} blended={blended_score:.3f} -> risk={risk} conf={confidence}")
            else:
                risk = kw_risk
                confidence = kw_confidence
                # Apply indirect ideation floor even when ML is unavailable
                # (same gating logic, but without route (b) since ML is absent)
                if len(evidence["indirect"]) > 0 and risk == "Low":
                    gated_only_no_ml = (len(evidence.get("gated_indirect", [])) > 0
                                        and len(evidence.get("ungated_indirect", [])) == 0
                                        and not evidence.get("gated_passes_kw", False))
                    if not gated_only_no_ml:
                        risk = "Moderate"
                        confidence = max(confidence, 0.60)
                        print(f"[PREDICT] INDIRECT IDEATION FLOOR (no ML): phrases={evidence['indirect']}")
                    else:
                        print(f"[PREDICT] CONTEXT GATE BLOCKED indirect floor (no ML): "
                              f"gated_phrases={evidence['gated_indirect']}")
                print(f"[PREDICT] NO ML: risk={risk} conf={confidence}")

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

            # ── Keep current_risk_level fresh on the user document ──────
            # Peer matching reads this field directly; it must reflect the
            # most recent /predict result, not a cached or missing value.
            # High-risk users are excluded from matching (see peer_routes.py).
            try:
                _db.users_collection.update_one(
                    {"_id": __import__("bson").ObjectId(identity)},
                    {"$set": {
                        "current_risk_level":   risk,
                        "risk_level_updated_at": datetime.now(timezone.utc),
                    }},
                )
            except Exception as risk_err:
                print(f"[WARN] Failed to update current_risk_level for user {identity}: {risk_err}")

        return jsonify({"risk": risk, "confidence": confidence})

    except Exception as e:
        print(f"[ERROR] {e}")
        return {"error": str(e)}, 500


if __name__ == "__main__":
    print("Starting MindEase API on http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=Config.PORT, debug=Config.DEBUG)