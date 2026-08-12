"""
utils/gibberish_check.py
────────────────────────────────────────────────────────────────────────────
Lightweight, dependency-free heuristic to detect non-language input
(keyboard-mashing, random consonant clusters, etc.) before running any
ML or keyword classification on it.

Algorithm
---------
For every whitespace-separated token (edge-punctuation stripped):
  - Skip tokens that are ≤ 1 character (handles "I", "a") or pure digits.
  - A token PASSES if it satisfies BOTH:
      (a) Contains at least one vowel in {a,e,i,o,u,y}
          ('y' included to catch "gym", "my", "ya", "yaar" etc.)
      (b) Has no run of more than MAX_CONSONANT_CLUSTER consecutive
          consonants (default: 4). Legitimate words rarely exceed this;
          gibberish like "gfutv" or "xnmzb" consistently do.
  - Count pass_fraction = passed / total_evaluated_tokens.

A text is flagged as "unanalyzable" when:
  pass_fraction < PASS_THRESHOLD  AND  token_count < MAX_TOKEN_COUNT

The short-text guard (MAX_TOKEN_COUNT) prevents accidentally filtering
longer, paragraph-length real entries that happen to contain unusual words.

Hinglish safety:
  Words like "theek", "nahi", "acha", "yaar", "kya", "hai", "hoon"
  all contain vowels and have no extreme consonant clusters → pass naturally.
"""

import re
import string

# ── Tuneable constants ────────────────────────────────────────────────────────
VOWELS                     = set("aeiouy")   # 'y' included deliberately
MAX_CONSONANT_CLUSTER_SHORT = 3              # max cluster for tokens with <=6 alpha chars
MAX_CONSONANT_CLUSTER_LONG  = 4              # max cluster for tokens with >6 alpha chars
MIN_VOWEL_RATIO            = 0.20            # for tokens >=5 alpha chars: need >=20% vowels
PASS_THRESHOLD             = 0.55            # <55% of tokens pass → suspicious
MAX_TOKEN_COUNT            = 20              # only apply check to short inputs
MIN_EVALUABLE_TOKENS       = 1              # need at least 1 evaluable token


def _strip_edge_punctuation(token: str) -> str:
    """Remove leading/trailing punctuation (e.g. commas, periods, quotes)."""
    return token.strip(string.punctuation)


def _max_consonant_run(word: str) -> int:
    """Return the length of the longest consecutive consonant run in word."""
    word_lower = word.lower()
    max_run = 0
    run = 0
    for ch in word_lower:
        if ch.isalpha() and ch not in VOWELS:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return max_run


def _token_passes(token: str) -> bool:
    """
    Return True if this token looks like a plausible word fragment.
    Criteria:
      (a) At least one vowel present
      (b) Consonant run no longer than MAX_CONSONANT_CLUSTER_SHORT (for short tokens)
          or MAX_CONSONANT_CLUSTER_LONG (for longer tokens)
      (c) For tokens with >=5 alphabetic chars: vowel-to-alpha ratio >= MIN_VOWEL_RATIO
          (1 vowel per 5 chars). This catches junk like 'jgfcuy' (1 vowel in 6 = 16.7%)
          while allowing real short words like 'theek' (2 vowels in 5 = 40%).
    """
    lower = token.lower()
    alpha_chars = [ch for ch in lower if ch.isalpha()]
    alpha_len = len(alpha_chars)
    vowels_in_token = [ch for ch in alpha_chars if ch in VOWELS]
    vowel_count = len(vowels_in_token)

    # (a) must have at least one vowel
    if vowel_count == 0:
        return False

    # (b) consonant cluster check — threshold depends on token length
    max_cluster = _max_consonant_run(token)
    cluster_limit = (
        MAX_CONSONANT_CLUSTER_SHORT if alpha_len <= 6
        else MAX_CONSONANT_CLUSTER_LONG
    )
    if max_cluster > cluster_limit:
        return False

    # (c) vowel density for longer tokens
    if alpha_len >= 5:
        vowel_ratio = vowel_count / alpha_len
        if vowel_ratio < MIN_VOWEL_RATIO:
            return False

    return True


def token_analysis(text: str) -> dict:
    """
    Analyse all tokens and return a detailed breakdown.
    Useful for testing and debugging.

    Returns:
        {
          "token_count":      int,   # total whitespace-split tokens
          "evaluated":        int,   # tokens actually scored (len > 1, not digits)
          "passed":           int,   # tokens that pass the heuristic
          "skipped":          int,   # tokens skipped (len <= 1 or pure digit)
          "pass_fraction":    float, # passed / evaluated (0.0 if evaluated == 0)
          "is_unanalyzable":  bool,
          "token_details":    list   # per-token breakdown
        }
    """
    raw_tokens = text.split()
    token_count = len(raw_tokens)

    evaluated = 0
    passed = 0
    skipped = 0
    details = []

    for raw in raw_tokens:
        stripped = _strip_edge_punctuation(raw)

        # Skip empty after stripping
        if not stripped:
            skipped += 1
            details.append({"raw": raw, "stripped": stripped, "status": "skipped_empty"})
            continue

        # Skip single-character tokens ("I", "a", "k") and pure digits
        if len(stripped) <= 1 or stripped.isdigit():
            skipped += 1
            details.append({"raw": raw, "stripped": stripped, "status": "skipped_short_or_digit"})
            continue

        evaluated += 1
        passes = _token_passes(stripped)
        if passes:
            passed += 1
        alpha_chars_d = [ch for ch in stripped.lower() if ch.isalpha()]
        vowel_count_d = sum(1 for ch in alpha_chars_d if ch in VOWELS)
        alpha_len_d = len(alpha_chars_d)
        details.append({
            "raw":               raw,
            "stripped":          stripped,
            "has_vowel":         vowel_count_d > 0,
            "vowel_count":       vowel_count_d,
            "alpha_len":         alpha_len_d,
            "vowel_ratio":       round(vowel_count_d / alpha_len_d, 3) if alpha_len_d else 0.0,
            "max_consonant_run": _max_consonant_run(stripped),
            "passes":            passes,
            "status":            "pass" if passes else "fail",
        })

    if evaluated < MIN_EVALUABLE_TOKENS:
        # Too few evaluable tokens to make a judgement — treat as analyzable
        pass_fraction = 1.0
    else:
        pass_fraction = passed / evaluated

    is_unanalyzable = (
        token_count < MAX_TOKEN_COUNT
        and pass_fraction < PASS_THRESHOLD
    )

    return {
        "token_count":     token_count,
        "evaluated":       evaluated,
        "passed":          passed,
        "skipped":         skipped,
        "pass_fraction":   round(pass_fraction, 4),
        "is_unanalyzable": is_unanalyzable,
        "token_details":   details,
    }


def is_unanalyzable(text: str) -> bool:
    """
    Public API.
    Returns True if the input looks like gibberish/non-language and should
    not be classified. Returns False if it looks like real text (including
    informal English, Hinglish, and other Latin-script languages).
    """
    return token_analysis(text)["is_unanalyzable"]
