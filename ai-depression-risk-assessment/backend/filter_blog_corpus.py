#!/usr/bin/env python3
"""
filter_blog_corpus.py
----------------------
Run this LOCALLY on your machine against the downloaded blogtext.csv
(Blog Authorship Corpus, ~800MB). Do NOT upload the raw file anywhere —
this script filters and samples it down to a small, safe CSV you can
then upload.

What it does:
  1. Keeps only 20s/30s age-group bloggers (skips 13s — teen diary
     entries in this corpus skew toward raw emotional intensity that
     has nothing to do with clinical depression but reads very
     negatively, and we don't want to mislabel that as "non-depression").
  2. Groups each blogger's posts by date and concatenates nearby posts
     until they reach journal length (60-150 words), matching the
     register of depression_dataset.csv.
  3. Runs every candidate document through the SAME crisis/moderate/mild
     keyword lists used in app.py's keyword_classify(), and DISCARDS
     any document that trips them. This is the safety filter — it
     ensures the negative class stays genuinely neutral/positive
     content, not just "not explicitly about depression."
  4. Strips corpus artifacts (urlLink tokens, HTML entities).
  5. Deduplicates and randomly samples down to a target count.
  6. Writes output in the same schema as depression_dataset.csv:
     clean_text,is_depression  (all rows here get is_depression=0)

Usage:
    python filter_blog_corpus.py --input blogtext.csv --output filtered_blog_sample.csv --target 4000
"""

import argparse
import csv
import html
import random
import re
import sys
from collections import defaultdict

# ── Same keyword lists as app.py's keyword_classify() ───────────────────
# Kept in sync manually for now — see Fix #3 in the consolidation plan
# (single source of truth for these lists) for the permanent solution.

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

MODERATE_RISK_KEYWORDS = [
    'depressed', 'depression', 'severely depressed', 'suicidal thoughts',
    'panic attack', 'no will to live', 'completely exhausted and numb',
    'numb inside', 'empty inside', 'hate myself', 'feel like a burden',
    'nobody cares', 'all alone', 'disconnected from', 'meaningless',
    "don't want to wake up", 'feel like disappearing', 'lost all hope',
    'no motivation whatsoever', 'crying all the time', 'deeply depressed',
]

MILD_NEGATIVE_KEYWORDS = [
    'sad', 'lonely', 'anxious', 'anxiety', 'stressed', 'stress', 'overwhelmed',
    'tired', 'exhausted', 'struggling', 'unmotivated', 'hard time', 'difficult',
    'worried', 'fear', 'insomnia', "can't sleep", 'low energy', 'withdrawn',
    'down', 'crying', 'cried', 'numb', 'flat', 'irritable', 'frustrated',
    'burned out', 'burnt out', 'lost', 'confused', 'empty', 'grief', 'grieving',
    'loss', 'heartbroken', 'hopeless', 'worthless', 'give up', 'no point',
    'no energy', 'not okay', 'falling apart', 'running on empty', 'no motivation',
    'isolating', 'withdrawing', "can't function", 'panic', 'dark days',
    'really dark', 'very dark', 'bad days', 'dark place', 'heavy mood',
    'miserable', 'dread', 'dreading', 'dreaded', 'guilt', 'guilty',
    'shame', 'ashamed', 'disconnected', 'detached', 'isolated', 'avoid',
]

# Also screen out a few extra red flags common in raw personal blogs
# that aren't in app.py's lists but shouldn't end up mislabeled as "fine":
EXTRA_SCREEN_KEYWORDS = [
    'self-harm', 'cutting myself', 'abuse', 'abused', 'trauma', 'ptsd',
    'eating disorder', 'anorexi', 'bulimi', 'divorce', 'died', 'death of',
    'funeral', 'grieve',
]

ALL_SCREEN_KEYWORDS = (
    HIGH_RISK_KEYWORDS + MODERATE_RISK_KEYWORDS + MILD_NEGATIVE_KEYWORDS
    + EXTRA_SCREEN_KEYWORDS
)

KEEP_AGE_MIN = 20
KEEP_AGE_MAX = 40  # covers the 20s and 30s buckets in the corpus

URL_TOKEN_RE = re.compile(r'\burlLink\b', re.IGNORECASE)
WHITESPACE_RE = re.compile(r'\s+')


def clean_text(raw: str) -> str:
    text = html.unescape(raw)
    text = URL_TOKEN_RE.sub('', text)
    text = WHITESPACE_RE.sub(' ', text).strip()
    return text


def trips_screen_keywords(text_lower: str) -> bool:
    return any(kw in text_lower for kw in ALL_SCREEN_KEYWORDS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Path to blogtext.csv')
    parser.add_argument('--output', default='filtered_blog_sample.csv')
    parser.add_argument('--target', type=int, default=4000,
                         help='Target number of output rows')
    parser.add_argument('--min-words', type=int, default=60)
    parser.add_argument('--max-words', type=int, default=150)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    # ── Pass 1: group posts by (blogger id, date) ───────────────────────
    # so we can concatenate a blogger's same-day posts into one
    # journal-length document instead of using tiny individual posts.
    grouped = defaultdict(list)
    total_rows = 0
    kept_age_rows = 0

    print("[1/3] Reading and grouping posts by blogger + date...")
    csv.field_size_limit(sys.maxsize)
    with open(args.input, encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            if total_rows % 200000 == 0:
                print(f"      ...{total_rows} rows read")
            try:
                age = int(row['age'])
            except (KeyError, ValueError):
                continue
            if not (KEEP_AGE_MIN <= age <= KEEP_AGE_MAX):
                continue
            kept_age_rows += 1
            key = (row['id'], row['date'])
            grouped[key].append(row['text'])

    print(f"      Total rows read: {total_rows}")
    print(f"      Rows in 20s/30s age range: {kept_age_rows}")
    print(f"      Grouped into {len(grouped)} blogger-day documents")

    # ── Pass 2: build candidate documents, clean, length-filter ─────────
    print("[2/3] Building and screening candidate documents...")
    candidates = []
    for posts in grouped.values():
        doc = clean_text(' '.join(posts))
        word_count = len(doc.split())
        if word_count < args.min_words or word_count > args.max_words:
            continue
        doc_lower = doc.lower()
        if trips_screen_keywords(doc_lower):
            continue
        candidates.append(doc)

    print(f"      Candidates passing length + safety filter: {len(candidates)}")

    if len(candidates) == 0:
        print("[ERROR] No candidates survived filtering. Check the input path/format.")
        sys.exit(1)

    # ── Pass 3: dedupe and sample ────────────────────────────────────────
    print("[3/3] Deduplicating and sampling...")
    unique_candidates = list(dict.fromkeys(candidates))  # preserve order, drop exact dupes
    random.shuffle(unique_candidates)
    sampled = unique_candidates[:args.target]

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['clean_text', 'is_depression'])
        for doc in sampled:
            writer.writerow([doc, 0])

    print(f"\n[OK] Wrote {len(sampled)} rows to {args.output}")
    print("[NEXT] Upload this file (NOT the original blogtext.csv) for merging into the training set.")


if __name__ == '__main__':
    main()
