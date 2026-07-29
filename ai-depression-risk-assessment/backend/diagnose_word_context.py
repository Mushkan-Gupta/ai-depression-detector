#!/usr/bin/env python3
"""
diagnose_word_context.py
------------------------
Diagnostic only. Reads files; does not write, train, or modify anything.

Outputs:
  1. File sizes and row/column counts for merged_depression_dataset.csv
  2. Per-source word frequency for 'happy' (Class 0 vs Class 1)
  3. Per-source word frequency for 'sad'   (Class 0 vs Class 1)
  4. 15 random Class-1 rows containing 'happy' (raw text)
  5. 15 random Class-0 rows containing 'sad'   (raw text)

Saved to: diagnose_word_context_output.txt  (with read-back verification)
"""

import os
import sys
import io
import re
import pandas as pd

# ---------------------------------------------------------------------------
# Tee: mirror stdout to a string buffer for saving
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
base_dir = os.path.dirname(os.path.abspath(__file__))

def whole_word_match(series, word):
    """Return boolean mask: rows where 'word' appears as a whole word (case-insensitive)."""
    pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
    return series.astype(str).str.contains(pattern, regex=True)

def word_breakdown(df_source, source_label, col, word):
    """Print class-stratified counts for a word in one source dataframe."""
    mask = whole_word_match(df_source[col], word)
    for cls in [0, 1]:
        cls_mask = df_source["is_depression"] == cls
        total_cls  = cls_mask.sum()
        match_cls  = (mask & cls_mask).sum()
        pct = (match_cls / total_cls * 100) if total_cls > 0 else 0.0
        print(f"    [{source_label}] Class {cls}: {match_cls:>5} / {total_cls:>6} rows contain '{word}' ({pct:.2f}%)")

# ===========================================================================
print("=" * 70)
print("  WORD CONTEXT DIAGNOSTIC")
print("=" * 70)

# ---------------------------------------------------------------------------
# 1. File size and shape of merged dataset
# ---------------------------------------------------------------------------
merged_path = os.path.join(base_dir, "merged_depression_dataset.csv")
size_bytes   = os.path.getsize(merged_path)
size_mb      = size_bytes / (1024 * 1024)

print(f"\n--- 1. merged_depression_dataset.csv ---")
print(f"  File size  : {size_bytes:,} bytes  ({size_mb:.2f} MB)")

df_merged = pd.read_csv(merged_path)
print(f"  Shape      : {df_merged.shape[0]:,} rows × {df_merged.shape[1]} columns")
print(f"  Columns    : {list(df_merged.columns)}")
print(f"  Label dist :")
print(df_merged["is_depression"].value_counts().to_string())

# Show byte length of a few sample rows
print(f"\n  Byte lengths of 5 random rows (raw clean_text field):")
sample5 = df_merged["clean_text"].dropna().sample(5, random_state=0)
for i, (idx, txt) in enumerate(sample5.items()):
    print(f"    row {idx:>5}: {len(txt.encode('utf-8')):>7} bytes | first 120 chars: {repr(txt[:120])}")

# Column-level memory usage
print(f"\n  Memory usage per column (bytes):")
for col in df_merged.columns:
    nbytes = df_merged[col].memory_usage(deep=True)
    print(f"    {col:<20}: {nbytes:>12,} bytes  ({nbytes/(1024*1024):.2f} MB)")

# ---------------------------------------------------------------------------
# Load the three source files
# ---------------------------------------------------------------------------
reddit_path  = os.path.join(base_dir, "depression_dataset.csv")
synth_path   = os.path.join(base_dir, "synthetic_journal_entries.csv")
blog_path    = os.path.join(base_dir, "filtered_blog_sample.csv")

df_reddit = pd.read_csv(reddit_path)
df_synth  = pd.read_csv(synth_path)
df_blog   = pd.read_csv(blog_path)

# Standardise: ensure 'is_depression' column exists and text col is 'clean_text'
sources = {
    "Reddit (depression_dataset.csv)"            : df_reddit,
    "Synthetic (synthetic_journal_entries.csv)"  : df_synth,
    "Blog (filtered_blog_sample.csv)"            : df_blog,
}

print(f"\n  Source file shapes (before merge filtering):")
for label, df in sources.items():
    print(f"    {label}: {df.shape[0]:,} rows, cols={list(df.columns)}")

# ---------------------------------------------------------------------------
# 2. 'happy' breakdown per source
# ---------------------------------------------------------------------------
print(f"\n--- 2. Word 'happy' — per-source, per-class counts ---")
for label, df in sources.items():
    print(f"  Source: {label}")
    if "clean_text" not in df.columns or "is_depression" not in df.columns:
        print(f"    [SKIP] Missing required columns. Cols: {list(df.columns)}")
        continue
    word_breakdown(df, label, "clean_text", "happy")

# Also show totals across merged dataset
print(f"\n  Totals across merged_depression_dataset.csv:")
mask_happy = whole_word_match(df_merged["clean_text"], "happy")
for cls in [0, 1]:
    cls_mask  = df_merged["is_depression"] == cls
    total_cls = cls_mask.sum()
    match_cls = (mask_happy & cls_mask).sum()
    pct = match_cls / total_cls * 100
    print(f"    Class {cls}: {match_cls:>5} / {total_cls:>6} rows ({pct:.2f}%)")

# ---------------------------------------------------------------------------
# 3. 'sad' breakdown per source
# ---------------------------------------------------------------------------
print(f"\n--- 3. Word 'sad' — per-source, per-class counts ---")
for label, df in sources.items():
    print(f"  Source: {label}")
    if "clean_text" not in df.columns or "is_depression" not in df.columns:
        print(f"    [SKIP] Missing required columns. Cols: {list(df.columns)}")
        continue
    word_breakdown(df, label, "clean_text", "sad")

print(f"\n  Totals across merged_depression_dataset.csv:")
mask_sad = whole_word_match(df_merged["clean_text"], "sad")
for cls in [0, 1]:
    cls_mask  = df_merged["is_depression"] == cls
    total_cls = cls_mask.sum()
    match_cls = (mask_sad & cls_mask).sum()
    pct = match_cls / total_cls * 100
    print(f"    Class {cls}: {match_cls:>5} / {total_cls:>6} rows ({pct:.2f}%)")

# ---------------------------------------------------------------------------
# 4. 15 random Class-1 rows containing 'happy'
# ---------------------------------------------------------------------------
print(f"\n--- 4. 15 random Class-1 (depression) rows containing 'happy' ---")
cls1_happy = df_merged[(df_merged["is_depression"] == 1) & mask_happy]["clean_text"]
n_available = len(cls1_happy)
print(f"  (Pool size: {n_available} rows)")
sample_cls1_happy = cls1_happy.sample(min(15, n_available), random_state=7)
for i, (idx, txt) in enumerate(sample_cls1_happy.items(), 1):
    print(f"\n  [{i:02d}] row {idx}:")
    print(f"  {txt}")

# ---------------------------------------------------------------------------
# 5. 15 random Class-0 rows containing 'sad'
# ---------------------------------------------------------------------------
print(f"\n--- 5. 15 random Class-0 (non-depression) rows containing 'sad' ---")
cls0_sad = df_merged[(df_merged["is_depression"] == 0) & mask_sad]["clean_text"]
n_available2 = len(cls0_sad)
print(f"  (Pool size: {n_available2} rows)")
sample_cls0_sad = cls0_sad.sample(min(15, n_available2), random_state=7)
for i, (idx, txt) in enumerate(sample_cls0_sad.items(), 1):
    print(f"\n  [{i:02d}] row {idx}:")
    print(f"  {txt}")

print(f"\n{'=' * 70}")
print("  END OF DIAGNOSTIC")
print(f"{'=' * 70}")

# ---------------------------------------------------------------------------
# Save and verify
# ---------------------------------------------------------------------------
sys.stdout = original_stdout
output_text = buf.getvalue()

out_path = os.path.join(base_dir, "diagnose_word_context_output.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(output_text)

print(output_text, end="")

with open(out_path, "r", encoding="utf-8") as f:
    readback = f.read()

match = (readback == output_text)
print(f"\n[SAVED]  {out_path}")
print(f"[VERIFY] Read-back matches: {match}")
