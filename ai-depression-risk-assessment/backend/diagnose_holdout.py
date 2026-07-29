import os
import datetime
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, log_loss

base_dir = os.path.dirname(os.path.abspath(__file__))

def main():
    print("============================================================")
    print("           HOLDOUT & MODEL DIAGNOSTICS CHECK")
    print("============================================================")

    # ------------------------------------------------------------------
    # 1. Timestamps and File Paths
    # ------------------------------------------------------------------
    model_path = os.path.join(base_dir, "depression_model.pkl")
    vec_path = os.path.join(base_dir, "vectorizer.pkl")
    keywords_path = os.path.join(base_dir, "constants", "keywords.py")

    print("\n--- 1. File Paths & Timestamps ---")
    if os.path.exists(model_path):
        mtime_model = os.path.getmtime(model_path)
        dt_model = datetime.datetime.fromtimestamp(mtime_model, tz=datetime.timezone.utc)
        print(f"Model Path:     {model_path}")
        print(f"Model MTime:    {dt_model.isoformat()} (UTC)")
    else:
        print(f"Model Path:     {model_path} (NOT FOUND)")

    if os.path.exists(keywords_path):
        mtime_kw = os.path.getmtime(keywords_path)
        dt_kw = datetime.datetime.fromtimestamp(mtime_kw, tz=datetime.timezone.utc)
        print(f"Keywords Path:  {keywords_path}")
        print(f"Keywords MTime: {dt_kw.isoformat()} (UTC)")
    else:
        print(f"Keywords Path:  {keywords_path} (NOT FOUND)")

    # ------------------------------------------------------------------
    # Load Model & Vectorizer
    # ------------------------------------------------------------------
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(vec_path, "rb") as f:
        vectorizer = pickle.load(f)

    # ------------------------------------------------------------------
    # 2. Dataset Split & Index Saving
    # ------------------------------------------------------------------
    data_path = os.path.join(base_dir, "merged_depression_dataset.csv")
    data = pd.read_csv(data_path)

    X_text = data["clean_text"].fillna("").astype(str)
    y = data["is_depression"]

    indices = np.arange(len(data))
    train_idx, test_idx, y_train, y_test = train_test_split(
        indices, y, test_size=0.2, random_state=42, stratify=y
    )

    indices_out_path = os.path.join(base_dir, "holdout_indices.npz")
    np.savez(indices_out_path, train_idx=train_idx, test_idx=test_idx)
    print(f"\n--- 2. Reproduce Train/Test Split ---")
    print(f"Split completed: {len(train_idx)} train, {len(test_idx)} test samples.")
    print(f"Saved holdout indices to: {indices_out_path}")

    # ------------------------------------------------------------------
    # 3. Metrics on Held-Out Set ONLY
    # ------------------------------------------------------------------
    X_test_text = X_text.iloc[test_idx]
    X_test_vec = vectorizer.transform(X_test_text)

    probs_test = model.predict_proba(X_test_vec)[:, 1]
    preds_test = model.predict(X_test_vec)

    loss_test = log_loss(y_test, model.predict_proba(X_test_vec))
    auc_test = roc_auc_score(y_test, probs_test)

    print("\n--- 3. Held-Out Evaluation (Test Set Only) ---")
    print(f"Log Loss: {loss_test:.4f}")
    print(f"ROC-AUC:  {auc_test:.4f}")
    print("\nClassification Report (Test Set Only):")
    print(classification_report(y_test, preds_test, target_names=["Class 0 (Non-Depression)", "Class 1 (Depression)"]))
    print("Confusion Matrix (Test Set Only):")
    print(confusion_matrix(y_test, preds_test))

    # ------------------------------------------------------------------
    # 4. Exact Coefficient Values for Target Words
    # ------------------------------------------------------------------
    print("\n--- 4. Target Word Coefficients ---")
    target_words = ["sad", "happy", "grateful", "good"]

    # Extract base estimator coefs
    if hasattr(model, 'calibrated_classifiers_'):
        base_lr = model.calibrated_classifiers_[0].estimator
    elif hasattr(model, 'coef_'):
        base_lr = model
    else:
        base_lr = None

    vocab = vectorizer.vocabulary_
    feature_names = vectorizer.get_feature_names_out()

    if base_lr and hasattr(base_lr, 'coef_'):
        coefs = base_lr.coef_[0]
        # Also compute average across all folds for comparison
        if hasattr(model, 'calibrated_classifiers_'):
            all_fold_coefs = [clf.estimator.coef_[0] for clf in model.calibrated_classifiers_]
            avg_coefs = np.mean(all_fold_coefs, axis=0)
        else:
            avg_coefs = coefs

        for w in target_words:
            if w in vocab:
                idx = vocab[w]
                c_val = coefs[idx]
                avg_val = avg_coefs[idx]
                print(f"Word: '{w}'")
                print(f"  Vocabulary Index: {idx}")
                print(f"  Fold 0 Coefficient: {c_val:.6f}")
                print(f"  5-Fold Mean Coefficient: {avg_val:.6f}")
            else:
                print(f"Word: '{w}' -> NOT IN VECTORIZER VOCABULARY")
    else:
        print("[WARN] Could not extract coefficients from model.")

    # ------------------------------------------------------------------
    # 5. Row Counts & Merge Filter Analysis
    # ------------------------------------------------------------------
    print("\n--- 5. Dataset Merge & Filtering Row Counts ---")
    df_main = pd.read_csv(os.path.join(base_dir, "depression_dataset.csv"))
    df_synth = pd.read_csv(os.path.join(base_dir, "synthetic_journal_entries.csv"))
    df_blog = pd.read_csv(os.path.join(base_dir, "filtered_blog_sample.csv"))

    count_main = len(df_main)
    count_synth = len(df_synth)
    count_blog = len(df_blog)
    sum_initial = count_main + count_synth + count_blog

    print(f"Rows from depression_dataset.csv (Reddit): {count_main}")
    print(f"Rows from synthetic_journal_entries.csv:  {count_synth}")
    print(f"Rows from filtered_blog_sample.csv:        {count_blog}")
    print(f"Total input rows across all 3 files:       {sum_initial}")

    # Re-simulate merge steps to show exact drops
    df_comb = pd.concat([df_main, df_synth, df_blog], ignore_index=True)
    
    # 1. Empty / invalid
    b_empty = len(df_comb)
    df_comb = df_comb.dropna(subset=["clean_text"])
    df_comb = df_comb[df_comb["clean_text"].astype(str).str.strip() != ""]
    drop_empty = b_empty - len(df_comb)

    # 2. < 3 words
    b_short = len(df_comb)
    df_comb["word_count"] = df_comb["clean_text"].astype(str).apply(lambda x: len(x.split()))
    df_comb = df_comb[df_comb["word_count"] >= 3]
    drop_short = b_short - len(df_comb)

    # 3. Deduplication
    b_dedup = len(df_comb)
    df_comb = df_comb.drop_duplicates(subset=["clean_text"])
    drop_dedup = b_dedup - len(df_comb)

    total_merged = len(data)

    print(f"\nMerge Pipeline Drops:")
    print(f"  Empty/invalid text dropped:            {drop_empty}")
    print(f"  Short texts (< 3 words) dropped:        {drop_short}")
    print(f"  Duplicate clean_text entries dropped:  {drop_dedup}")
    print(f"  Total dropped during merge:             {drop_empty + drop_short + drop_dedup}")
    print(f"Total final rows in merged_depression_dataset.csv: {total_merged}")

    print("\n============================================================")

if __name__ == "__main__":
    main()
