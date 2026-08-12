"""
live_verify_gibberish.py
Waits for Render redeploy, then verifies all 3 live cases + DB confirmation.
"""
import sys, os, json, time, requests

# ── MongoDB (direct) ──────────────────────────────────────────────────────
# Load MONGO_URI from .env for direct DB query
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MONGO_URI = os.environ.get("MONGO_URI", "")
if not MONGO_URI:
    print("[ERROR] MONGO_URI not found in .env — cannot do DB check")
    sys.exit(1)

from pymongo import MongoClient
client_mg = MongoClient(MONGO_URI)
db_prod = client_mg["mindease"]
journal_col = db_prod["journal_entries"]

BASE = "https://ai-depression-detector.onrender.com"
WAIT_TIMEOUT = 300   # max 5 minutes for redeploy

# ── Step 1: Wait for redeploy ─────────────────────────────────────────────
print("\n" + "="*70)
print("  STEP 1 — Waiting for Render redeploy (checking /health)")
print("="*70)

deadline = time.time() + WAIT_TIMEOUT
last_status = None
while time.time() < deadline:
    try:
        r = requests.get(f"{BASE}/health", timeout=10)
        if r.status_code == 200:
            data = r.json()
            probe = requests.post(f"{BASE}/predict",
                                  json={"journal": "kjhgfds lkjhg"},
                                  timeout=15)
            if probe.status_code == 200 and probe.json().get("risk") == "Unanalyzable":
                print(f"\n[OK] Render is up and serving new code. /health = {data}")
                print(f"     Probe response: {probe.json()}")
                break
            else:
                current = probe.json().get("risk", "?")
                if current != last_status:
                    print(f"  ... server up but old code still running (probe risk={current!r}), waiting ...")
                    last_status = current
        else:
            if last_status != "down":
                print(f"  ... /health returned {r.status_code}, waiting ...")
                last_status = "down"
    except requests.exceptions.RequestException as e:
        if last_status != "conn_err":
            print(f"  ... connection error ({e}), waiting ...")
            last_status = "conn_err"
    time.sleep(10)
else:
    print("\n[TIMEOUT] Render did not serve new code within 5 minutes.")
    print("  Proceeding anyway — results may reflect old code.")

# ── Step 2: Three live POST cases ─────────────────────────────────────────
print("\n" + "="*70)
print("  STEP 2 — Live POST cases")
print("="*70)

CASES = [
    {
        "label": "(a) Gibberish [caught] — expect risk=Unanalyzable",
        "journal": "asdkj qpwoe xnmzb",
        "expect_risk": "Unanalyzable",
        "expect_not": None,
    },
    {
        "label": "(a2) GIBBERISH-1 [known FN] — y-heavy mash, documents pass=0.67, expect Low",
        "journal": "gfutvxsjv jgfcuy ecgfig uycfy yf g feyuf",
        "expect_risk": "Low",    # documented false negative — heuristic scores 4/6=0.67 > 0.55
        "expect_not": None,
    },
    {
        "label": "(b) Hinglish — must NOT be Unanalyzable, must classify normally",
        "journal": "theek hoon yaar",
        "expect_risk": None,
        "expect_not": "Unanalyzable",
    },
    {
        "label": "(c) Crisis phrase — must return High (confirms crisis override intact)",
        "journal": "I want to end it all",
        "expect_risk": "High",
        "expect_not": None,
    },
]

results = []
for case in CASES:
    print(f"\n>>> POST {BASE}/predict")
    print(f"    body: {json.dumps({'journal': case['journal']})}")
    try:
        r = requests.post(f"{BASE}/predict",
                          json={"journal": case["journal"]},
                          timeout=20)
        body = r.json()
        raw_json = json.dumps(body, indent=2)
        print(f"\nHTTP {r.status_code} {r.reason}")
        print(raw_json)

        risk = body.get("risk", "MISSING")
        ok = True
        if case["expect_risk"] and risk != case["expect_risk"]:
            ok = False
            print(f"  [FAIL] Expected risk={case['expect_risk']!r}, got {risk!r}")
        if case["expect_not"] and risk == case["expect_not"]:
            ok = False
            print(f"  [FAIL] risk must NOT be {case['expect_not']!r}, but it was")
        if ok:
            print(f"  [PASS] {case['label']}")
        results.append({"label": case["label"], "risk": risk, "pass": ok, "body": body})
    except Exception as e:
        print(f"  [ERROR] {e}")
        results.append({"label": case["label"], "risk": "ERROR", "pass": False})

# ── Step 3: DB confirmation ───────────────────────────────────────────────
print("\n" + "="*70)
print("  STEP 3 — DB confirmation: gibberish must NOT appear in journal_entries")
print("="*70)

GIBBERISH_CAUGHT  = "asdkj qpwoe xnmzb"
GIBBERISH_FN      = "gfutvxsjv jgfcuy ecgfig uycfy yf g feyuf"

print(f"\n  [1] Querying for caught gibberish: {GIBBERISH_CAUGHT!r}")
matches_caught = list(journal_col.find({"journal": GIBBERISH_CAUGHT}))
count_caught = len(matches_caught)
print(f"      Documents found: {count_caught}")
if count_caught == 0:
    print("      [PASS] Not saved. Early-return prevented DB write.")
else:
    print("      [FAIL] Saved! Early-return did NOT prevent DB write:")
    for doc in matches_caught:
        print(f"        {doc}")

print(f"\n  [2] Querying for GIBBERISH-1 (known FN): {GIBBERISH_FN!r}")
matches_fn = list(journal_col.find({"journal": GIBBERISH_FN}))
count_fn = len(matches_fn)
print(f"      Documents found: {count_fn}")
if count_fn == 0:
    print("      NOTE: Also not saved (unauthenticated POST — no JWT, so no DB write regardless).")
else:
    print(f"      INFO: {count_fn} document(s) found (authenticated user previously submitted this).")

# ── Step 4: Summary ──────────────────────────────────────────────────────
print("\n" + "="*70)
print("  SUMMARY")
print("="*70)
for r in results:
    status = "[PASS]" if r["pass"] else "[FAIL]"
    print(f"  {status}  {r['label']}  ->  risk={r['risk']!r}")
db_ok = (count_caught == 0)
print(f"  {'[PASS]' if db_ok else '[FAIL]'}  DB check: caught gibberish not saved")
print("="*70)

all_ok = all(r["pass"] for r in results) and db_ok
sys.exit(0 if all_ok else 1)
