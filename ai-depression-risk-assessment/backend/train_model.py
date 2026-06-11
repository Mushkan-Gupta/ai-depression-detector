#!/usr/bin/env python3
"""
MindEase Improved Model Trainer v2
- Adds TF-IDF length normalization (norm='l2') to handle long journal entries
- Uses balanced class weights
- Uses calibrated probabilities for reliable thresholding  
- bigrams for richer feature matching
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, confusion_matrix
import pickle
import os

base_dir     = os.path.dirname(os.path.abspath(__file__))
csv_path     = os.path.join(base_dir, "depression_dataset.csv")

print("[INFO] Loading dataset...")
data = pd.read_csv(csv_path)
print(f"[INFO] Dataset size: {len(data)} rows")
print(f"[INFO] Label distribution:\n{data['is_depression'].value_counts()}\n")

X = data["clean_text"].fillna("").astype(str)
y = data["is_depression"]

# ─── TF-IDF with L2 norm ──────────────────────────────────────────────────
# norm='l2' ensures document vectors have unit length regardless of length.
# This is the KEY fix — without it, longer texts get higher TF-IDF sum scores.
vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=20000,
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    sublinear_tf=True,   # log(1 + tf) — dampens frequency dominance
    norm="l2",           # L2-normalise each document row → length-invariant
)

X_vec = vectorizer.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(
    X_vec, y, test_size=0.2, random_state=42, stratify=y
)

# ─── Logistic Regression with class balancing ─────────────────────────────
base_lr = LogisticRegression(
    C=0.8,           # Slightly stronger regularisation for generalisation
    max_iter=1000,
    solver="lbfgs",
    class_weight="balanced",
    random_state=42,
)

model = CalibratedClassifierCV(base_lr, cv=5, method="sigmoid")
model.fit(X_train, y_train)

# ─── Evaluation ───────────────────────────────────────────────────────────
y_pred = model.predict(X_test)
acc    = model.score(X_test, y_test)

print(f"[RESULT] Test Accuracy: {acc:.4f}  ({round(acc*100,2)}%)")
print("\n[RESULT] Classification Report:")
print(classification_report(y_test, y_pred, target_names=["No Depression", "Depression"]))
print("[RESULT] Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

cv_scores = cross_val_score(model, X_vec, y, cv=5, scoring="accuracy")
print(f"\n[RESULT] 5-Fold CV: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# ─── Probability analysis ─────────────────────────────────────────────────
proba_sample = model.predict_proba(X_test[:300])
dep_probs    = proba_sample[:, 1]
actual       = np.array(y_test)[:300]

non_dep_probs = dep_probs[actual == 0]
dep_only      = dep_probs[actual == 1]

print(f"\n[INFO] Probability distribution on test set:")
print(f"  Non-depression (label=0): mean={non_dep_probs.mean():.3f}  median={np.median(non_dep_probs):.3f}  p75={np.percentile(non_dep_probs,75):.3f}")
print(f"  Depression     (label=1): mean={dep_only.mean():.3f}  median={np.median(dep_only):.3f}  p25={np.percentile(dep_only,25):.3f}")
print(f"  Suggested threshold range: [{np.percentile(non_dep_probs,90):.3f} – {np.percentile(dep_only,10):.3f}]")

# ─── Save ─────────────────────────────────────────────────────────────────
model_out = os.path.join(base_dir, "depression_model.pkl")
vec_out   = os.path.join(base_dir, "vectorizer.pkl")

with open(model_out, "wb") as f: pickle.dump(model, f)
with open(vec_out,   "wb") as f: pickle.dump(vectorizer, f)

print(f"\n[OK] Saved model -> {model_out}")
print(f"[OK] Saved vectorizer -> {vec_out}")
print("[INFO] Restart app.py to reload.\n")