# -*- coding: utf-8 -*-
"""
full_demo_test.py - MindEase Comprehensive Demo & Test Suite
Registers a user, submits 6 journal entries (2 per category),
retrieves history, and prints a full structured report.
"""
import requests, json, time, sys

BASE = "http://127.0.0.1:5000"
ts = int(time.time())

JOURNALS = [
    # ── LOW RISK ────────────────────────────────────────────────────────────
    {
        "id": "L1", "expected": "Low", "emotion": "Happiness & Gratitude",
        "text": (
            "Today has been one of those rare days where everything just clicks. "
            "I woke up before my alarm, had a long run in the crisp morning air, "
            "and finished my coffee while watching the sunrise from the balcony. "
            "There is something quietly powerful about starting the day on your "
            "own terms.\n\n"
            "At work, I finished a project that I have been building for three "
            "months. My manager praised the effort in front of the whole team, "
            "and I genuinely felt proud — not in an arrogant way, just a calm "
            "sense of having done something meaningful and done it well.\n\n"
            "This evening I video-called my best friend who moved abroad last "
            "year. We laughed for two hours straight. I feel grateful, connected, "
            "and hopeful about where my life is heading. I am sleeping well, "
            "eating well, and genuinely looking forward to tomorrow. Life feels "
            "good right now."
        )
    },
    {
        "id": "L2", "expected": "Low", "emotion": "Motivation & Recovery",
        "text": (
            "Six months ago I was in a really dark place — burnt out, exhausted, "
            "and barely keeping up with daily responsibilities. I started therapy "
            "in January and it has been transformative. I am writing this entry "
            "to document how far I have come.\n\n"
            "I now wake up with purpose most mornings. I have built small habits: "
            "journaling, a ten-minute meditation, and a short walk before work. "
            "These things used to feel impossible. Now they feel natural. My "
            "therapist says I have shown remarkable progress and I am starting to "
            "believe her.\n\n"
            "I still have hard days, but they no longer consume me. I feel "
            "energetic, motivated, and genuinely excited about the future. I "
            "signed up for a photography class next month — something I have "
            "always wanted to try. Recovery is not a straight line, but I am "
            "moving in the right direction and I feel calm and supported in "
            "doing so."
        )
    },

    # ── MODERATE RISK ────────────────────────────────────────────────────────
    {
        "id": "M1", "expected": "Moderate", "emotion": "Stress & Anxiety",
        "text": (
            "I cannot seem to catch a break lately. Work deadlines keep piling up "
            "and I am constantly anxious about falling behind. I stay late almost "
            "every night, get home exhausted, and then lie awake for hours "
            "worrying about the next day. The insomnia is the worst part — I can "
            "feel my body shutting down but my mind will not stop racing.\n\n"
            "I have been stressed and overwhelmed for weeks now. I used to enjoy "
            "cooking dinner but lately I just grab whatever requires zero effort "
            "because I am too tired to do anything. Social plans keep getting "
            "cancelled because I do not have the energy. I feel like I am "
            "withdrawing from everything I used to care about.\n\n"
            "I know this is not sustainable. I am struggling to find a way out "
            "of this cycle. I am not okay right now, but I am trying to take it "
            "one day at a time. I booked a GP appointment for next week because "
            "I need some help managing this stress before it gets worse."
        )
    },
    {
        "id": "M2", "expected": "Moderate", "emotion": "Sadness & Loneliness",
        "text": (
            "It has been three months since the breakup and I still cry almost "
            "every day. I thought it would get easier by now but some days the "
            "grief just crashes back in like a wave. I miss having someone to "
            "talk to at the end of the day. The flat feels so empty and I feel "
            "deeply lonely in a way that is hard to put into words.\n\n"
            "I have been isolating a lot. My friends invite me out but I always "
            "cancel at the last minute because I feel too sad and heavy to fake "
            "being okay. I know that is not healthy but I do not have the energy "
            "to pretend. I feel disconnected from the people around me even when "
            "I am physically with them.\n\n"
            "I lost all motivation to pursue the hobbies I used to love. The gym "
            "membership I was so proud of has gone unused for two months. I feel "
            "empty inside most of the time. I know I need to reach out for help "
            "and I booked a counselling session for next week. I am hopeful that "
            "talking to someone will help me process this grief."
        )
    },

    # ── HIGH RISK ────────────────────────────────────────────────────────────
    {
        "id": "H1", "expected": "High", "emotion": "Hopelessness & Suicidal Ideation",
        "text": (
            "I do not see the point anymore. I wake up every morning and the "
            "first thought I have is that I do not want to be alive. It is not "
            "a passing feeling — it has been there every single day for weeks "
            "and it is getting louder, not quieter. I am completely numb inside "
            "and everything feels meaningless.\n\n"
            "I have been thinking about ending my life. I keep searching online "
            "for methods and I know that is a bad sign but I cannot stop. I "
            "feel like a burden to everyone around me and I genuinely believe "
            "they would be better off without me. I hate myself deeply. I feel "
            "completely disconnected from reality and from everyone I love.\n\n"
            "I have lost all hope that things will ever get better. I do not "
            "want to exist anymore. I have not eaten properly in days and I "
            "cannot sleep. If anyone reads this, please know I am in a very "
            "dark place and I desperately need help."
        )
    },
    {
        "id": "H2", "expected": "High", "emotion": "Crisis & Self-Harm",
        "text": (
            "I cannot keep going like this. The pain is unbearable and I do not "
            "know how to make it stop. I have been thinking about hurting myself "
            "as a way to feel something — anything — other than this suffocating "
            "emptiness. I know it is wrong but rational thinking has stopped "
            "working for me.\n\n"
            "I want to die. I have thought about how I would end it all and it "
            "scares me that the thought brings me more relief than fear. I no "
            "longer want to exist. I am searching for ways to end my life and "
            "I feel like I am standing at the very edge. I feel completely alone "
            "and worthless. Nobody cares, and even if they do, I am too far "
            "gone to believe it.\n\n"
            "I am writing this because a tiny part of me is still holding on. "
            "I do not want to die — I want the pain to end. I called a crisis "
            "line tonight but hung up before anyone answered. I am terrified. "
            "Please, someone, I need help right now."
        )
    },
]

# ─────────────────────────────────────────────────────────────────────────────
def separator(title="", char="=", w=65):
    if title:
        pad = (w - len(title) - 2) // 2
        print(f"\n{char*pad} {title} {char*pad}")
    else:
        print(char * w)

results = []

# STEP 0 - health check
separator("STEP 0: Health Check")
try:
    r = requests.get(f"{BASE}/", timeout=5)
    assert r.status_code == 200
    print(f"  API Status : {r.json()['status']}")
    print(f"  Model Loaded: {r.json()['model_loaded']}")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# STEP 1 - register
separator("STEP 1: Register Demo User")
email = f"demo_{ts}@mindease-demo.com"
r = requests.post(f"{BASE}/auth/register",
    json={"name": "Demo User", "email": email, "password": "Demo1234"},
    timeout=10)
assert r.status_code == 201, f"Register failed: {r.text}"
token   = r.json()["access_token"]
user    = r.json()["user"]
user_id = user["id"]
print(f"  User ID    : {user_id}")
print(f"  Email      : {email}")
print(f"  JWT Token  : {token[:50]}...")
HEADERS = {"Authorization": f"Bearer {token}"}

# STEP 2 - submit all journals
separator("STEP 2: Submit 6 Journal Entries")
for j in JOURNALS:
    r = requests.post(f"{BASE}/predict",
        json={"journal": j["text"]},
        headers=HEADERS, timeout=15)
    assert r.status_code == 200, f"Predict failed: {r.text}"
    payload = r.json()
    j["actual"]     = payload["risk"]
    j["confidence"] = payload["confidence"]
    j["passed"]     = (j["actual"] == j["expected"])
    results.append(j)
    status = "PASS" if j["passed"] else "FAIL"
    print(f"  [{j['id']}] Expected={j['expected']:<10} Got={j['actual']:<10} "
          f"Conf={j['confidence']:.3f}  [{status}]")

# STEP 3 - retrieve history
time.sleep(0.3)
separator("STEP 3: Verify MongoDB Storage (GET /history)")
r = requests.get(f"{BASE}/history?page_size=10", headers=HEADERS, timeout=10)
assert r.status_code == 200, f"History failed: {r.text}"
history = r.json()
entries = history["entries"]
print(f"  Total stored: {history['total']}")
print(f"  Page       : {history['page']} / {history['total_pages']}")
print()
for i, e in enumerate(entries, 1):
    snippet = e["journal"][:60].replace("\n", " ")
    print(f"  [{i}] _id={e['id']}")
    print(f"       risk={e['risk']}  conf={e['confidence']}  "
          f"stored_at={e['created_at']}")
    print(f"       text: \"{snippet}...\"")

# STEP 4 - emit raw JSON for report
separator("STEP 4: Raw JSON Payload")
print(json.dumps({
    "user": {"id": user_id, "email": email},
    "db_collection": "mindease.journal_entries",
    "stored_fields": ["_id", "user_id", "journal", "risk", "confidence", "created_at"],
    "total_entries_stored": history["total"],
    "entries_sample": [{
        "id": e["id"], "risk": e["risk"],
        "confidence": e["confidence"], "created_at": e["created_at"]
    } for e in entries]
}, indent=2))

# STEP 5 - summary table
separator("STEP 5: Test Summary Table")
passed = sum(1 for j in results if j["passed"])
print(f"\n  {'ID':<5} {'Emotion':<35} {'Exp':<12} {'Got':<12} {'Conf':<8} {'Result'}")
print(f"  {'-'*80}")
for j in results:
    status = "PASS" if j["passed"] else "FAIL"
    print(f"  {j['id']:<5} {j['emotion']:<35} {j['expected']:<12} "
          f"{j['actual']:<12} {j['confidence']:<8} {status}")
print(f"\n  Passed: {passed}/{len(results)}")
separator()
