import pandas as pd
import numpy as np
import pickle
import os
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, log_loss

base_dir = os.path.dirname(os.path.abspath(__file__))

def diagnose():
    print("="*60)
    print("           MODEL DIAGNOSTICS")
    print("="*60)
    
    # 1. Load Data
    data_path = os.path.join(base_dir, "merged_depression_dataset.csv")
    if not os.path.exists(data_path):
        print(f"[ERROR] Dataset not found at {data_path}")
        return
    data = pd.read_csv(data_path)
    X = data["clean_text"].fillna("").astype(str)
    y = data["is_depression"]
    
    print("\n--- Dataset Statistics ---")
    print(f"Total samples: {len(data)}")
    for lbl, count in y.value_counts().items():
        print(f"  Class {lbl}: {count} ({count/len(data)*100:.1f}%)")

    # 2. Load Model & Vectorizer
    model_path = os.path.join(base_dir, "depression_model.pkl")
    vec_path = os.path.join(base_dir, "vectorizer.pkl")
    
    if not os.path.exists(model_path) or not os.path.exists(vec_path):
        print("[ERROR] Model or vectorizer missing.")
        return
        
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(vec_path, "rb") as f:
        vectorizer = pickle.load(f)
        
    # 3. Feature Coefficients & Bigrams
    # We'll extract coefficients from one of the calibrated classifiers for inspection
    print("\n--- Feature Analysis ---")
    if hasattr(model, 'calibrated_classifiers_'):
        # Extract base estimator from the first fold
        base_lr = model.calibrated_classifiers_[0].estimator
    elif hasattr(model, 'coef_'):
        base_lr = model
    else:
        base_lr = None
        
    if base_lr and hasattr(base_lr, 'coef_'):
        feature_names = vectorizer.get_feature_names_out()
        coefs = base_lr.coef_[0]
        
        # Sort indices
        sorted_indices = np.argsort(coefs)
        
        print("\nTop 20 words pushing towards NON-DEPRESSION (Class 0):")
        for idx in sorted_indices[:20]:
            print(f"  {feature_names[idx]:<15} : {coefs[idx]:.4f}")
            
        print("\nTop 20 words pushing towards DEPRESSION (Class 1):")
        for idx in sorted_indices[-20:][::-1]:
            print(f"  {feature_names[idx]:<15} : {coefs[idx]:.4f}")
            
        # Also let's find some informative bigrams specifically
        bigram_indices = [i for i, name in enumerate(feature_names) if ' ' in name]
        if bigram_indices:
            bigram_coefs = [(feature_names[i], coefs[i]) for i in bigram_indices]
            bigram_coefs.sort(key=lambda x: x[1])
            print("\nTop 10 BIGRAMS pushing towards NON-DEPRESSION:")
            for name, val in bigram_coefs[:10]:
                print(f"  {name:<20} : {val:.4f}")
            print("\nTop 10 BIGRAMS pushing towards DEPRESSION:")
            for name, val in bigram_coefs[-10:][::-1]:
                print(f"  {name:<20} : {val:.4f}")
    else:
        print("[WARN] Could not extract coefficients from model.")

    # 4. Calibration & Predictions
    print("\n--- Calibration & Predictions (Full Dataset) ---")
    X_vec = vectorizer.transform(X)
    probs = model.predict_proba(X_vec)[:, 1]
    preds = model.predict(X_vec)
    
    loss = log_loss(y, probs)
    auc = roc_auc_score(y, probs)
    print(f"Log Loss: {loss:.4f}")
    print(f"ROC-AUC:  {auc:.4f}")
    
    # 5. False Positives & False Negatives (Sample)
    print("\n--- Error Analysis (Sample) ---")
    fp_indices = np.where((y == 0) & (preds == 1))[0]
    fn_indices = np.where((y == 1) & (preds == 0))[0]
    
    print(f"Total False Positives: {len(fp_indices)}")
    if len(fp_indices) > 0:
        print("Example False Positives (Label=0, Pred=1):")
        for idx in np.random.choice(fp_indices, min(3, len(fp_indices)), replace=False):
            print(f"  [Prob: {probs[idx]:.3f}] {X.iloc[idx][:100]}...")
            
    print(f"\nTotal False Negatives: {len(fn_indices)}")
    if len(fn_indices) > 0:
        print("Example False Negatives (Label=1, Pred=0):")
        for idx in np.random.choice(fn_indices, min(3, len(fn_indices)), replace=False):
            print(f"  [Prob: {probs[idx]:.3f}] {X.iloc[idx][:100]}...")
            
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    diagnose()
