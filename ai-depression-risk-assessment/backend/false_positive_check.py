"""
false_positive_check.py
=======================
Runs 8 ordinary, non-crisis sentences through the live /predict pipeline.
Reports risk, confidence, whether crisis resources are shown, and
specifically whether the INDIRECT IDEATION FLOOR or LOW-CONFIDENCE FLOOR
was activated (detectable from app.py log lines).

NO code changes — verification only.
"""
import os
import sys
import io

sys.path.insert(0, os.path.dirname(__file__))

# Capture stdout from app.py so we can show which floor (if any) was activated
import unittest.mock as mock

FP_CASES = [
    "I want to disappear for a quiet weekend at the lake, just need a break from everyone.",
    "I'm so tired of fighting traffic every morning on my commute.",
    "I'm finally done with this assignment, what a relief.",
    "Sometimes I just want to sleep in on Saturdays and do nothing.",
    "I wish I could just fall asleep the second I get home, work wore me out.",
    "I'm ready to go home, this trip has been exhausting.",
    "There's no point arguing with him, he never listens anyway.",
    "I keep wishing I could just disappear into a good book for a whole day.",
]

from app import app, keyword_classify, INDIRECT_IDEATION_PHRASES

print("=" * 80)
print("  FALSE POSITIVE CHECK -- 8 ordinary non-crisis sentences")
print("  (checking for incorrectly triggered indirect ideation / low-conf floors)")
print("=" * 80)
print()

with app.test_client() as client:
    for i, phrase in enumerate(FP_CASES, 1):
        lower = phrase.lower()

        # --- Show which indirect phrases match (if any) ---
        matched = [p for p in INDIRECT_IDEATION_PHRASES if p in lower]

        # Capture log output from predict() to catch floor messages
        captured = io.StringIO()
        import sys as _sys
        old_stdout = _sys.stdout
        _sys.stdout = captured

        response = client.post('/predict', json={'journal': phrase})

        _sys.stdout = old_stdout
        log_output = captured.getvalue()

        data = response.get_json()
        risk = data.get('risk', 'Low')
        conf = data.get('confidence', 0.0)

        indirect_floor = "INDIRECT FLOOR FIRED" in log_output or "INDIRECT IDEATION FLOOR" in log_output
        lowconf_floor  = "LOW-CONFIDENCE FLOOR" in log_output

        crisis_shown   = risk in ("Moderate", "High")

        # Determine overall verdict
        if risk == "Low":
            verdict = "[OK - Low as expected]"
        elif risk == "Moderate" and not matched and not lowconf_floor:
            verdict = "[REVIEW - Moderate with no floor trigger]"
        elif risk == "Moderate" and (matched or indirect_floor or lowconf_floor):
            verdict = "[FALSE POSITIVE - floor triggered incorrectly]"
        else:
            verdict = "[OK]"

        print(f"Case {i}: {phrase[:75]}{'...' if len(phrase)>75 else ''}")
        print(f"  Risk: {risk:<10}  Conf: {conf:.1%}  Crisis shown: {'YES' if crisis_shown else 'no'}")
        print(f"  Indirect phrase matches: {matched if matched else 'none'}")
        print(f"  Indirect floor fired:    {'YES' if indirect_floor else 'no'}")
        print(f"  Low-conf floor fired:    {'YES' if lowconf_floor else 'no'}")
        print(f"  Verdict: {verdict}")
        print()

print("=" * 80)
