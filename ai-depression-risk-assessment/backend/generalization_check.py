"""
Generalization check: 6 new short phrases not seen before (never in test suite or Case 2/4).
Prints token count, ml_prob, blended score, final risk for each.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))

from app import app, keyword_classify, model, vectorizer

PHRASES = [
    # 3 short positive (new wording)
    ("SHORT-POS-A", "Feeling really good today, so full of energy and joy."),
    ("SHORT-POS-B", "I am excited and content, everything is going well."),
    ("SHORT-POS-C", "Had a great morning, feeling positive and motivated."),
    # 3 short depressive (new wording)
    ("SHORT-DEP-A", "I feel hopeless and empty, nothing matters anymore."),
    ("SHORT-DEP-B", "Feeling so low and worthless lately, hard to function."),
    ("SHORT-DEP-C", "Everything feels dark and pointless, I am exhausted and miserable."),
]

with app.test_client() as client:
    for label, phrase in PHRASES:
        token_count = len(phrase.split())
        
        # Get ml_prob directly
        if model is not None and vectorizer is not None:
            vec = vectorizer.transform([phrase])
            proba = model.predict_proba(vec)[0]
            ml_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])
        else:
            ml_prob = None

        # Get keyword layer
        kw_risk, kw_conf, evidence, neg_score = keyword_classify(phrase)
        norm_neg = 1 / (1 + math.exp(-4 * (neg_score - 0.5)))

        # Blending weights
        if token_count < 15:
            W_KW, W_ML = 0.8, 0.2
        else:
            W_KW, W_ML = 0.6, 0.4
        blended = (W_KW * norm_neg) + (W_ML * ml_prob) if ml_prob is not None else norm_neg

        # Map to risk
        if blended >= 0.65:
            risk_label = "High"
        elif blended >= 0.32:
            risk_label = "Moderate"
        else:
            risk_label = "Low"

        print(f"[{label}] tokens={token_count:2d} | ml_prob={ml_prob:.3f} | norm_neg={norm_neg:.3f} | "
              f"neg_score={neg_score:.2f} | W_KW={W_KW} | blended={blended:.3f} | risk={risk_label}")
        print(f"         Phrase: '{phrase}'")
        print()
