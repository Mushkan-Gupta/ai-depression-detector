"""
test_context_gate_generalization.py
====================================
5 NEW test sentences that use "tired of fighting", "want to disappear",
or "ready to go" in ordinary non-crisis contexts DIFFERENT from the
3 known false-positive examples (lake/traffic/home).

This confirms the context gate generalizes and is not tuned to specific
test cases.

Expected: ALL 5 should resolve to Low/normal risk.
"""
import os
import sys
import io

sys.path.insert(0, os.path.dirname(__file__))

from app import app, INDIRECT_IDEATION_PHRASES, CONTEXT_GATED_PHRASES

GENERALIZATION_CASES = [
    # "tired of fighting" in mundane contexts (not traffic)
    "I'm tired of fighting with this printer, it keeps jamming every ten minutes.",
    "My kids are tired of fighting over the remote, so we got a second TV.",
    # "want to disappear" in mundane contexts (not lake)
    "After this deadline I want to disappear to a beach resort for two weeks.",
    # "ready to go" in mundane contexts (not home)
    "The car is packed and we're ready to go on our road trip to the mountains!",
    "I've finished my warmup, I'm ready to go for the race.",
]

print("=" * 80)
print("  CONTEXT GATE GENERALIZATION TEST -- 5 novel non-crisis sentences")
print("  (using gated phrases in everyday contexts NOT seen before)")
print("=" * 80)
print()

all_pass = True
with app.test_client() as client:
    for i, phrase in enumerate(GENERALIZATION_CASES, 1):
        lower = phrase.lower()

        matched = [p for p in INDIRECT_IDEATION_PHRASES if p in lower]
        gated   = [p for p in matched if p in CONTEXT_GATED_PHRASES]

        # Capture log output
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        response = client.post('/predict', json={'journal': phrase})

        sys.stdout = old_stdout
        log_output = captured.getvalue()

        data = response.get_json()
        risk = data.get('risk', 'Low')
        conf = data.get('confidence', 0.0)

        gate_blocked = "CONTEXT GATE BLOCKED" in log_output

        if risk == "Low":
            verdict = "[OK - Low as expected]"
        else:
            verdict = "[FALSE POSITIVE - should be Low]"
            all_pass = False

        print(f"Case {i}: {phrase[:75]}{'...' if len(phrase)>75 else ''}")
        print(f"  Risk: {risk:<10}  Conf: {conf:.1%}")
        print(f"  Indirect matches: {matched if matched else 'none'}")
        print(f"  Gated phrases:    {gated if gated else 'none'}")
        print(f"  Gate blocked:     {'YES' if gate_blocked else 'no'}")
        print(f"  Verdict: {verdict}")
        print()

print("=" * 80)
if all_pass:
    print("[PASS] ALL 5 novel cases correctly resolved to Low.")
else:
    print("[FAIL] Some cases still triggered false positives -- review above.")
print("=" * 80)
