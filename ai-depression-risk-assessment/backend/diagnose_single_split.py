#!/usr/bin/env python3
"""
diagnose_single_split.py
------------------------
Diagnostic-only script. Does NOT overwrite depression_model.pkl,
vectorizer.pkl, or train_model.py.

Purpose:
    Fit a PLAIN (uncalibrated, no CV) LogisticRegression on EXACTLY the same
    80/20 train_test_split used by train_model.py, using the SAME TfidfVectorizer
    parameters and the SAME LR hyperparameters (C=0.8, solver=lbfgs, etc.).

    Produces one coefficient vector — nothing more — and reports:
      • Coefficients for target words: sad, happy, grateful, good
      • Accuracy / F1 / ROC-AUC on the held-out 20%

Output: printed to console AND saved to diagnose_single_split_output.txt
        in the same directory as this script.
"""

import os
import sys
import io
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    accuracy_score,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
base_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(base_dir, "merged_depression_dataset.csv")
out_path  = os.path.join(base_dir, "diagnose_single_split_output.txt")

# ---------------------------------------------------------------------------
# Tee: write to both stdout and a string buffer so we can save it later
# ---------------------------------------------------------------------------
class Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            s.write(data)
    def flush(self):
        for s in self.streams:
            s.flush()

buf = io.StringIO()
original_stdout = sys.stdout
sys.stdout = Tee(original_stdout, buf)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
print("=" * 60)
print("  SINGLE-SPLIT PLAIN LR DIAGNOSTIC")
print("  (No calibration, no cross-validation)")
print("=" * 60)

# 1. Load data
print(f"\n[1] Loading: {data_path}")
data = pd.read_csv(data_path)
print(f"    Rows: {len(data)}")
print(f"    Label distribution:\n{data['is_depression'].value_counts().to_string()}")

X_text = data["clean_text"].fillna("").astype(str)
y      = data["is_depression"]

# 2. TF-IDF — IDENTICAL parameters to train_model.py
print("\n[2] Fitting TfidfVectorizer (same params as train_model.py):")
print("    stop_words='english', max_features=20000, ngram_range=(1,2),")
print("    min_df=2, max_df=0.95, sublinear_tf=True, norm='l2'")

vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=20000,
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    sublinear_tf=True,
    norm="l2",
)
X_vec = vectorizer.fit_transform(X_text)
print(f"    Vocabulary size: {len(vectorizer.vocabulary_)}")
print(f"    Feature matrix shape: {X_vec.shape}")

# 3. EXACT split from train_model.py
print("\n[3] Applying ONLY this split:")
print("    train_test_split(X_vec, y, test_size=0.2, random_state=42, stratify=y)")
X_train, X_test, y_train, y_test = train_test_split(
    X_vec, y, test_size=0.2, random_state=42, stratify=y
)
print(f"    Train rows: {X_train.shape[0]}")
print(f"    Test  rows: {X_test.shape[0]}")

# 4. Plain LogisticRegression — IDENTICAL hyperparameters to train_model.py's base_lr
print("\n[4] Fitting PLAIN LogisticRegression (no CalibratedClassifierCV, no CV):")
print("    C=0.8, max_iter=1000, solver='lbfgs',")
print("    class_weight='balanced', random_state=42")

lr = LogisticRegression(
    C=0.8,
    max_iter=1000,
    solver="lbfgs",
    class_weight="balanced",
    random_state=42,
)
lr.fit(X_train, y_train)
print("    Fit complete. Single coefficient vector produced.")

# 5. Coefficients for target words
print("\n[5] Coefficient values for target words")
print("    (from the ONE model fitted on the 80% train partition above)")
print("-" * 50)
target_words = ["sad", "happy", "grateful", "good"]
vocab = vectorizer.vocabulary_
coefs = lr.coef_[0]

for w in target_words:
    if w in vocab:
        idx = vocab[w]
        print(f"  Word: '{w}'")
        print(f"    Vocabulary index : {idx}")
        print(f"    Coefficient      : {coefs[idx]:.8f}")
    else:
        print(f"  Word: '{w}' -> NOT IN VOCABULARY")

# 6. Performance on the held-out 20%
print("\n[6] Performance on held-out test set (20%)")
print("-" * 50)
y_pred  = lr.predict(X_test)
y_proba = lr.predict_proba(X_test)[:, 1]

acc    = accuracy_score(y_test, y_pred)
auc    = roc_auc_score(y_test, y_proba)

print(f"  Accuracy : {acc:.6f}")
print(f"  ROC-AUC  : {auc:.6f}")
print("\n  Classification Report:")
print(classification_report(
    y_test, y_pred,
    target_names=["Class 0 (Non-Depression)", "Class 1 (Depression)"]
))
print("  Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

print("\n" + "=" * 60)
print("  END OF DIAGNOSTIC")
print("=" * 60)

# ---------------------------------------------------------------------------
# Restore stdout and save output file
# ---------------------------------------------------------------------------
sys.stdout = original_stdout
output_text = buf.getvalue()

with open(out_path, "w", encoding="utf-8") as f:
    f.write(output_text)

print(output_text, end="")  # ensure it shows in terminal if piped
print(f"\n[SAVED] Output written to: {out_path}")

# Verification read-back
with open(out_path, "r", encoding="utf-8") as f:
    readback = f.read()

match = (readback == output_text)
print(f"[VERIFY] Read-back matches printed output: {match}")
