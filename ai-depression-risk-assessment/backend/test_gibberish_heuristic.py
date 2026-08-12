#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_gibberish_heuristic.py - Phase 2 standalone test (NO Flask, NO ML model)
─────────────────────────────────────────────────────────────────────────────
Run this BEFORE wiring the heuristic into /predict.

Usage:
    python test_gibberish_heuristic.py

Exit code 0 = all cases passed (proceed to Phase 3).
Exit code 1 = at least one false positive on a legitimate entry (STOP — do not wire in).
"""

import sys
import os

# Allow running from the backend directory directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.gibberish_check import token_analysis

# ─────────────────────────────────────────────────────────────────────────────
# TEST CASES
# Each entry: (label, text, expect_flagged: bool, note)
# ─────────────────────────────────────────────────────────────────────────────

GIBBERISH_CASES = [
    # True gibberish — ALL must be flagged (expect_flagged = True)
    (
        "GIBBERISH-1",
        "gfutvxsjv jgfcuy ecgfig uycfy yf g feyuf",
        True,
        "From the spec: classic random-cluster mash",
    ),
    (
        "GIBBERISH-2",
        "asdkj qpwoe xnmzb",
        True,
        "From the spec: 3-token keyboard smash",
    ),
    (
        "GIBBERISH-3",
        "kjhgfds lkjhg",
        True,
        "Home-row left-hand smash",
    ),
    (
        "GIBBERISH-4",
        "zxcvbnm asdfgh qwerty",
        True,
        "Keyboard layout rows — no real words",
    ),
    (
        "GIBBERISH-5",
        "xkqz vpwm bnrt",
        True,
        "Pure consonant clusters, zero vowels",
    ),
]

LEGITIMATE_CASES = [
    # Legitimate short entries — NONE must be flagged (expect_flagged = False)
    (
        "LEGIT-1",
        "im sad",
        False,
        "Informal but real English",
    ),
    (
        "LEGIT-2",
        "cant sleep",
        False,
        "Common complaint, informal English",
    ),
    (
        "LEGIT-3",
        "ok",
        False,
        "Single short real word (1 evaluable token after skip guard)",
    ),
    (
        "LEGIT-4",
        "fine i guess",
        False,
        "Short real phrase with single-char skip",
    ),
    (
        "LEGIT-5",
        "I am okay",
        False,
        "Baseline real sentence",
    ),
    (
        "LEGIT-6",
        "theek hoon yaar",
        False,
        "Hinglish: 'I'm fine, friend' — CRITICAL Hinglish case",
    ),
    (
        "LEGIT-7",
        "nahi pata kya karoon",
        False,
        "Hinglish: 'don't know what to do' — CRITICAL Hinglish case",
    ),
    (
        "LEGIT-8",
        "acha hai sab",
        False,
        "Hinglish: 'everything is okay' — CRITICAL Hinglish case",
    ),
    (
        "LEGIT-9",
        "just one word",
        False,
        "Simple 3-word English phrase",
    ),
    (
        "LEGIT-10",
        "cry",
        False,
        "Single real word",
    ),
    (
        "LEGIT-11",
        "not feeling great today",
        False,
        "Informal real statement of distress",
    ),
    (
        "LEGIT-12",
        "thoda stress hai",
        False,
        "Hinglish: 'a little stress' — CRITICAL Hinglish case",
    ),
]

ALL_CASES = GIBBERISH_CASES + LEGITIMATE_CASES

# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

COL_WIDTHS = {
    "id":       12,
    "expect":   10,
    "got":      10,
    "ratio":    16,
    "tokens":   8,
    "result":   8,
}

def run_all():
    print()
    print("=" * 80)
    print("  PHASE 2 — Gibberish Heuristic Standalone Test")
    print("  (No Flask, no ML model, pure heuristic only)")
    print("=" * 80)
    print()

    header = (
        f"  {'ID':<{COL_WIDTHS['id']}}"
        f"{'Expected':<{COL_WIDTHS['expect']}}"
        f"{'Got':<{COL_WIDTHS['got']}}"
        f"{'PassRatio':<{COL_WIDTHS['ratio']}}"
        f"{'Tokens':<{COL_WIDTHS['tokens']}}"
        f"{'Result'}"
    )
    print(header)
    print("  " + "-" * 76)

    false_positives = []   # legit cases wrongly flagged
    false_negatives = []   # gibberish cases not flagged

    for label, text, expect_flagged, note in ALL_CASES:
        analysis = token_analysis(text)
        got_flagged = analysis["is_unanalyzable"]
        passed_ok = (got_flagged == expect_flagged)

        # Build ratio string: "passed/evaluated"
        ratio_str = f"{analysis['passed']}/{analysis['evaluated']} = {analysis['pass_fraction']:.2f}"

        expect_str = "FLAGGED" if expect_flagged else "OK"
        got_str    = "FLAGGED" if got_flagged    else "OK"
        result_str = "[PASS]" if passed_ok else "[FAIL]"

        print(
            f"  {label:<{COL_WIDTHS['id']}}"
            f"{expect_str:<{COL_WIDTHS['expect']}}"
            f"{got_str:<{COL_WIDTHS['got']}}"
            f"{ratio_str:<{COL_WIDTHS['ratio']}}"
            f"{analysis['token_count']:<{COL_WIDTHS['tokens']}}"
            f"{result_str}"
        )

        # Per-token detail
        for td in analysis["token_details"]:
            if td["status"] == "skipped_short_or_digit" or td["status"] == "skipped_empty":
                print(f"    -> '{td['raw']}' : {td['status']}")
            else:
                vowel_flag = f"+vowel({td['vowel_count']}/{td['alpha_len']}={td['vowel_ratio']:.2f})"
                cluster_flag = f"cluster={td['max_consonant_run']}"
                pass_flag = "+" if td["passes"] else "-"
                print(f"    -> '{td['stripped']}' : {vowel_flag}  {cluster_flag}  [{pass_flag}]")

        print(f"    NOTE: {note}")
        print()

        if not passed_ok:
            if expect_flagged and not got_flagged:
                false_negatives.append(label)
            elif not expect_flagged and got_flagged:
                false_positives.append(label)

    # ─── Summary ────────────────────────────────────────────────────────────
    total   = len(ALL_CASES)
    correct = total - len(false_positives) - len(false_negatives)

    print("=" * 80)
    print(f"  Results: {correct}/{total} correct")

    if false_positives:
        print()
        print("  [STOP] FALSE POSITIVES (legitimate entries wrongly flagged):")
        for fp in false_positives:
            print(f"     - {fp}")
        print()
        print("  !! STOP: Do NOT wire heuristic into /predict until these are resolved.")
        print("  !! A real user's genuine entry would be blocked.")
        print()

    if false_negatives:
        print()
        print("  [WARN] FALSE NEGATIVES (gibberish not caught):")
        for fn in false_negatives:
            print(f"     - {fn}")

    if not false_positives and not false_negatives:
        print()
        print("  [OK] ALL CASES PASS - heuristic is clean.")
        print("  [OK] Proceed to Phase 3: wire into /predict.")

    print("=" * 80)
    print()

    # Exit code: fail if any false positive (the dangerous failure mode)
    return len(false_positives) == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
