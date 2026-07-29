"""
test_indirect_ideation.py
=========================
Tests phrases that express hopelessness, exhaustion, or wanting to give up
WITHOUT using any explicit crisis keyword already in HIGH_RISK_KEYWORDS.
This is an honest detection gap audit -- not tuned to pass.

Each phrase is run through the FULL /predict pipeline (keyword + ML blend).
For each case we report: risk level, confidence, and whether crisis hotlines
would be displayed (i.e. risk == Moderate or High).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app

# 15 indirect ideation phrases — no "suicide", "kill myself", "want to die",
# "self harm", "overdose", or any other HIGH_RISK_KEYWORDS term.
INDIRECT_CASES = [
    # The exact failure phrase reported by the user
    "i m done i m tired of fighting i want to rest now",
    # Core indirect patterns
    "I'm so tired of fighting every single day. I just want to rest.",
    "I can't do this anymore. I'm completely exhausted and I don't see the point.",
    "Everyone would be better off without me around. I'm just a burden.",
    "I just want it to stop. I want everything to stop.",
    "I don't want to be here anymore. I'm so done with all of this.",
    "I wish I could just disappear and not have to deal with any of this.",
    "I'm ready to go. I've had enough of this struggle.",
    "There's no reason to keep going. Nothing is going to change.",
    "I'm done fighting. I have no energy left and I can't keep going like this.",
    # Slightly more indirect / metaphorical
    "I keep wishing I could just fall asleep and not wake up. I'm so exhausted.",
    "I think my family would have an easier life if I wasn't causing all this trouble.",
    "I used to fight so hard but I can't take this anymore. I am done.",
    "Sometimes I think about how peaceful it would be to just... stop. To rest permanently.",
    "Every morning I wake up and think, what's the point? I can't see a future for myself.",
]

print("=" * 70)
print("  INDIRECT IDEATION DETECTION TEST")
print("  (No HIGH_RISK_KEYWORDS used — indirect language only)")
print("=" * 70)
print(f"{'#':<3} {'Risk':<10} {'Conf':<8} {'Crisis Shown?':<15} Phrase")
print("-" * 70)

all_pass = True
with app.test_client() as client:
    for i, phrase in enumerate(INDIRECT_CASES, 1):
        response = client.post('/predict', json={'journal': phrase})
        data = response.get_json()
        risk = data.get('risk', 'Low')
        conf = data.get('confidence', 0.0)
        crisis_shown = "YES [CRISIS]" if risk in ("Moderate", "High") else "NO [MISSED]"
        if risk == "Low":
            all_pass = False
        display_phrase = phrase[:55] + "..." if len(phrase) > 55 else phrase
        print(f"{i:<3} {risk:<10} {conf:<8.2%} {crisis_shown:<15} {display_phrase}")

print("-" * 70)
if all_pass:
    print("\n[PASS] ALL CASES: Crisis resources would be shown (none resolved to Low).")
else:
    print("\n[WARN] SOME CASES resolved to Low -- review phrases above marked 'NO [MISSED]'.")
print()
