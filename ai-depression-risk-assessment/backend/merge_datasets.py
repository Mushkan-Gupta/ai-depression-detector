import pandas as pd
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

def merge_datasets():
    print("[INFO] Starting data merge process...")

    # Load datasets
    df_main = pd.read_csv(os.path.join(base_dir, "depression_dataset.csv"))
    df_synthetic = pd.read_csv(os.path.join(base_dir, "synthetic_journal_entries.csv"))
    df_blog = pd.read_csv(os.path.join(base_dir, "filtered_blog_sample.csv"))
    
    # Ensure they have the correct schema
    for name, df in [("depression_dataset", df_main), ("synthetic_journal", df_synthetic), ("filtered_blog", df_blog)]:
        if "clean_text" not in df.columns or "is_depression" not in df.columns:
            print(f"[ERROR] {name} is missing required columns.")
            return

    initial_total = len(df_main) + len(df_synthetic) + len(df_blog)
    print(f"[INFO] Initial rows: {initial_total} (Main: {len(df_main)}, Synthetic: {len(df_synthetic)}, Blog: {len(df_blog)})")

    # Concatenate
    df_combined = pd.concat([df_main, df_synthetic, df_blog], ignore_index=True)

    # 1. Remove empty/invalid samples
    before_empty_drop = len(df_combined)
    df_combined = df_combined.dropna(subset=["clean_text"])
    df_combined = df_combined[df_combined["clean_text"].str.strip() != ""]
    empty_removed = before_empty_drop - len(df_combined)
    print(f"[INFO] Removed {empty_removed} empty/invalid samples.")

    # 2. Filter extremely short texts (< 3 words)
    before_short_drop = len(df_combined)
    df_combined["word_count"] = df_combined["clean_text"].astype(str).apply(lambda x: len(x.split()))
    df_combined = df_combined[df_combined["word_count"] >= 3]
    short_removed = before_short_drop - len(df_combined)
    print(f"[INFO] Removed {short_removed} short samples (< 3 words).")

    # 3. Deduplicate
    before_dedup = len(df_combined)
    df_combined = df_combined.drop_duplicates(subset=["clean_text"])
    dedup_removed = before_dedup - len(df_combined)
    print(f"[INFO] Removed {dedup_removed} duplicate samples.")

    # Save
    out_path = os.path.join(base_dir, "merged_depression_dataset.csv")
    df_combined[["clean_text", "is_depression"]].to_csv(out_path, index=False)
    
    # Print stats
    print("\n" + "="*40)
    print("      FINAL DATASET STATISTICS")
    print("="*40)
    print(f"Total samples: {len(df_combined)}")
    print("Class Distribution:")
    counts = df_combined['is_depression'].value_counts()
    for label, count in counts.items():
        print(f"  Class {label}: {count} ({count/len(df_combined)*100:.1f}%)")
    
    avg_length = df_combined['word_count'].mean()
    print(f"Average text length: {avg_length:.1f} words")
    print(f"Saved to: {out_path}")
    print("="*40 + "\n")

if __name__ == "__main__":
    merge_datasets()
