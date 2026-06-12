# -*- coding: utf-8 -*-
"""
test_journal_mongodb.py
=======================
End-to-end test that:
  1. Registers a test user (or logs in if already registered)
  2. Submits 3 distinct journal paragraphs to POST /predict
  3. Calls GET /history to verify the entries were stored in MongoDB
  4. Prints a clear PASS / FAIL summary for each step

Run from the backend/ directory:
    python test_journal_mongodb.py
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def ok(msg):   print(f"  [PASS]  {msg}")
def fail(msg): print(f"  [FAIL]  {msg}")
def info(msg): print(f"  [INFO]  {msg}")
def section(title): print(f"\n{'='*60}\n  {title}\n{'='*60}")

# ── Test user credentials ─────────────────────────────────────────────────────
# Unique timestamp suffix so re-runs don't collide
ts         = int(time.time())
TEST_EMAIL = f"testuser_{ts}@mindease-test.com"
TEST_PASS  = "Test1234"
TEST_NAME  = "MindEase Tester"

# ── Three journal paragraphs ──────────────────────────────────────────────────
JOURNALS = [
    # 1 – Low risk (positive / neutral)
    (
        "Paragraph 1 (Expected: Low risk)",
        """Today was actually a pretty good day. I went for a morning walk and felt 
        refreshed and energetic by the time I got home. I had a productive work session 
        and managed to finish a project I had been procrastinating on for weeks. 
        In the evening I cooked a proper meal, called my mom, and watched a show I enjoy. 
        I feel grateful for the small moments of calm and connection. Looking forward 
        to tomorrow and feeling hopeful that things are moving in a positive direction."""
    ),

    # 2 – Moderate risk (stress / sadness keywords)
    (
        "Paragraph 2 (Expected: Moderate risk)",
        """I have been feeling really overwhelmed lately and I am not sure how to cope. 
        Work has been extremely stressful and I keep waking up at 3 am unable to go back 
        to sleep. I feel anxious almost every day and there is a constant sense of dread 
        that I cannot shake. I feel lonely even when I am surrounded by people. 
        I have been crying more than usual and I just feel tired and exhausted all the time. 
        I am struggling to find motivation to do even basic tasks. I know I should reach 
        out to someone but I feel like a burden and nobody really cares."""
    ),

    # 3 – High risk (crisis-level keywords)
    (
        "Paragraph 3 (Expected: High risk)",
        """I do not want to be alive anymore. I have been thinking about ending my life 
        and I keep searching online for methods. Everything feels completely pointless 
        and I feel like I am better off dead. I hate myself and I cannot see any reason 
        to keep going. I have lost all hope and I feel like disappearing forever. 
        The pain is unbearable and I feel completely disconnected from everyone around me. 
        I do not want to exist. Please, if anyone is reading this, I need help."""
    ),
]

# ═════════════════════════════════════════════════════════════════════════════
# STEP 0 — Health check
# ═════════════════════════════════════════════════════════════════════════════
section("STEP 0 — API Health Check")
try:
    r = requests.get(f"{BASE_URL}/", timeout=5)
    if r.status_code == 200:
        ok(f"API is up  ->  {r.json()}")
    else:
        fail(f"Unexpected status {r.status_code}: {r.text}")
except requests.exceptions.ConnectionError:
    fail(f"Cannot connect to {BASE_URL}. Is the Flask server running?")
    print(f"\n  Start it with:  python app.py\n")
    raise SystemExit(1)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — Register test user
# ═════════════════════════════════════════════════════════════════════════════
section("STEP 1 — Register Test User")
info(f"Email : {TEST_EMAIL}")
info(f"Name  : {TEST_NAME}")

token = None

r = requests.post(
    f"{BASE_URL}/auth/register",
    json={"name": TEST_NAME, "email": TEST_EMAIL, "password": TEST_PASS},
    timeout=10,
)

if r.status_code == 201:
    data  = r.json()
    token = data.get("access_token")
    user  = data.get("user", {})
    ok(f"Registered successfully  →  user_id={user.get('id')}")
    ok(f"JWT token received       ->  {token[:40]}...")
elif r.status_code == 409:
    info("Email already exists — trying login instead")
    r2 = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASS},
        timeout=10,
    )
    if r2.status_code == 200:
        token = r2.json().get("access_token")
        ok(f"Logged in successfully   ->  token={token[:40]}...")
    else:
        fail(f"Login failed: {r2.status_code} {r2.text}")
        raise SystemExit(1)
else:
    fail(f"Registration failed: {r.status_code} {r.text}")
    raise SystemExit(1)

HEADERS = {"Authorization": f"Bearer {token}"}

# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — Submit 3 journal paragraphs
# ═════════════════════════════════════════════════════════════════════════════
section("STEP 2 — Submit 3 Journal Paragraphs to POST /predict")

results = []   # (label, risk, confidence)

for label, text in JOURNALS:
    print(f"\n  >> {label}")
    r = requests.post(
        f"{BASE_URL}/predict",
        json={"journal": text},
        headers=HEADERS,
        timeout=15,
    )
    if r.status_code == 200:
        payload    = r.json()
        risk       = payload.get("risk", "?")
        confidence = payload.get("confidence", "?")
        results.append((label, risk, confidence))
        ok(f"Risk={risk}  Confidence={confidence}")
    else:
        fail(f"Status {r.status_code}: {r.text}")
        results.append((label, "ERROR", 0))

# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 — Verify entries in MongoDB via GET /history
# ═════════════════════════════════════════════════════════════════════════════
section("STEP 3 — Verify MongoDB Storage via GET /history")

# Small delay to allow async writes (shouldn't be needed but safe)
time.sleep(0.5)

r = requests.get(
    f"{BASE_URL}/history",
    headers=HEADERS,
    timeout=10,
)

if r.status_code != 200:
    fail(f"GET /history returned {r.status_code}: {r.text}")
else:
    history_data = r.json()
    # Support both {"entries": [...]} and a plain list
    entries = history_data.get("entries") or history_data.get("data") or history_data
    if not isinstance(entries, list):
        fail(f"Unexpected history shape: {json.dumps(history_data)[:200]}")
    else:
        ok(f"History endpoint returned {len(entries)} entries total")

        # The 3 we just submitted should be among the most recent
        recent = entries[:3]   # newest-first ordering assumed

        if len(entries) >= 3:
            ok(f"At least 3 entries found in MongoDB [OK]")
        else:
            fail(f"Only {len(entries)} entries found — expected at least 3")

        print(f"\n  Most recent 3 entries from MongoDB:")
        for i, entry in enumerate(recent, 1):
            print(f"\n    [{i}] risk={entry.get('risk')}  "
                  f"confidence={entry.get('confidence')}  "
                  f"created_at={entry.get('created_at')}")
            snippet = (entry.get('journal') or entry.get('text') or '')[:80]
            print(f"        text snippet: \"{snippet}...\"")

# ═════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
section("FINAL SUMMARY")
print(f"\n  {'Label':<45} {'Risk':<12} {'Confidence'}")
print(f"  {'-'*70}")
for label, risk, conf in results:
    print(f"  {label:<45} {risk:<12} {conf}")

print(f"\n  MongoDB verification:")
if 'entries' in dir() and isinstance(entries, list) and len(entries) >= 3:
    ok("All 3 journal entries confirmed stored in MongoDB [OK]")
else:
    fail("Could not confirm all 3 entries in MongoDB [FAIL]")

print(f"\n{'='*60}\n")
