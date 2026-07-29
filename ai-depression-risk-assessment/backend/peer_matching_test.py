"""
peer_matching_test.py — End-to-end test suite for /peer/opt-in, /peer/opt-out,
and /peer/candidates.

Scenarios (a) through (h) as specified:
  a) Register 2 users with overlapping themes; User A opts in -> empty candidates
  b) User B opts in -> User A's candidate list now includes User B
  c) GET /peer/candidates as User A -> User B appears
  d) Third user: current_risk_level="High", opted-in, overlapping themes
     -> never appears in any candidate list
  e) High-risk user attempts POST /peer/opt-in -> 403 with crisis guidance,
     available_for_matching NOT set to true
  f) Bidirectional exclusion: add User A to User B's excluded_users ->
     neither sees the other
  g) Theme overlap = 0 case -> no match shown

All requests are real HTTP calls to localhost:5000.
All raw status codes and response bodies are printed verbatim.
"""

import json
import sys
import requests
from bson import ObjectId
import db as _db
from flask import Flask
from config import Config

BASE = "http://127.0.0.1:5000"

# ── Bootstrap DB (needed only to set test fields directly) ─────────────────
_app = Flask(__name__)
_app.config.from_object(Config)
_db.init_db(_app)

SEP = "=" * 70

def _req(method, path, token=None, body=None, label=""):
    """Make a request and print raw status + body."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = BASE + path
    resp = getattr(requests, method)(url, headers=headers,
                                     json=body, timeout=10)
    print(f"\n  [{label}] {method.upper()} {path}")
    print(f"  HTTP {resp.status_code}")
    try:
        body_out = json.dumps(resp.json(), indent=4)
    except Exception:
        body_out = resp.text
    print(f"  {body_out}")
    return resp

def _register(email, password, name):
    r = requests.post(f"{BASE}/auth/register",
                      json={"email": email, "password": password, "name": name},
                      timeout=10)
    if r.status_code not in (200, 201, 409):
        print(f"[FAIL] register {email}: {r.status_code} {r.text}")
        sys.exit(1)
    if r.status_code == 409:
        # User exists — log in instead
        r2 = requests.post(f"{BASE}/auth/login",
                           json={"email": email, "password": password},
                           timeout=10)
        return r2.json()["access_token"], r2.json()["user"]["id"]
    return r.json()["access_token"], r.json()["user"]["id"]

def _consent(token):
    r = requests.post(f"{BASE}/peer/consent",
                      headers={"Authorization": f"Bearer {token}",
                               "Content-Type": "application/json"},
                      timeout=10)
    assert r.status_code == 200, f"consent failed: {r.status_code} {r.text}"

def _set_user_fields(user_id_str, **fields):
    """Directly patch user document in MongoDB for test setup."""
    _db.users_collection.update_one(
        {"_id": ObjectId(user_id_str)},
        {"$set": fields}
    )

def _get_user(user_id_str):
    return _db.users_collection.find_one({"_id": ObjectId(user_id_str)})

# ── Setup ──────────────────────────────────────────────────────────────────
print(SEP)
print("SETUP: Registering test users and giving peer consent")
print(SEP)

tok_a, id_a = _register("peer_test_a@example.com", "TestPass1", "PeerUserA")
tok_b, id_b = _register("peer_test_b@example.com", "TestPass1", "PeerUserB")
tok_c, id_c = _register("peer_test_c@example.com", "TestPass1", "PeerUserC")  # High-risk
tok_d, id_d = _register("peer_test_d@example.com", "TestPass1", "PeerUserD")  # zero overlap

_consent(tok_a); _consent(tok_b); _consent(tok_c); _consent(tok_d)

# Set test state directly in DB
_set_user_fields(id_a,
    themes=["anxiety", "loneliness", "grief"],
    current_risk_level="Low",
    peer_display_name="UserA-Anon",
    available_for_matching=False,
    matching_started_at=None,
    excluded_users=[],
)
_set_user_fields(id_b,
    themes=["anxiety", "grief", "sleep"],
    current_risk_level="Moderate",
    peer_display_name="UserB-Anon",
    available_for_matching=False,
    matching_started_at=None,
    excluded_users=[],
)
_set_user_fields(id_c,
    themes=["anxiety", "loneliness"],
    current_risk_level="High",
    peer_display_name="UserC-Anon",
    available_for_matching=False,   # start opted out
    matching_started_at=None,
    excluded_users=[],
)
_set_user_fields(id_d,
    themes=["work_stress"],         # zero overlap with A/B
    current_risk_level="Low",
    peer_display_name="UserD-Anon",
    available_for_matching=False,
    matching_started_at=None,
    excluded_users=[],
)

print(f"  User A: id={id_a}  themes=[anxiety,loneliness,grief]  risk=Low")
print(f"  User B: id={id_b}  themes=[anxiety,grief,sleep]        risk=Moderate")
print(f"  User C: id={id_c}  themes=[anxiety,loneliness]         risk=High")
print(f"  User D: id={id_d}  themes=[work_stress]                risk=Low")


# ══════════════════════════════════════════════════════════════════════════
# (a) User A opts in — B not opted in yet -> empty candidates
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (a): User A opts in. B/C/D not opted in -> empty candidate list")
print(SEP)
r = _req("post", "/peer/opt-in", token=tok_a, label="A opt-in")
assert r.status_code == 200, f"FAIL expected 200 got {r.status_code}"
body = r.json()
assert body["candidates"] == [], f"FAIL expected empty list, got {body['candidates']}"
print("  [PASS] User A opt-in 200, candidates = []")


# ══════════════════════════════════════════════════════════════════════════
# (b) User B opts in -> User A should now appear in B's candidate list
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (b): User B opts in -> B's response includes User A in candidates")
print(SEP)
r = _req("post", "/peer/opt-in", token=tok_b, label="B opt-in")
assert r.status_code == 200, f"FAIL expected 200 got {r.status_code}"
body = r.json()
cand_ids = [c["candidate_id"] for c in body["candidates"]]
assert id_a in cand_ids, f"FAIL expected User A ({id_a}) in candidates, got {cand_ids}"
a_entry = next(c for c in body["candidates"] if c["candidate_id"] == id_a)
overlap_got = set(a_entry["overlapping_themes"])
overlap_expected = {"anxiety", "grief"}
assert overlap_got == overlap_expected, (
    f"FAIL expected overlap {overlap_expected}, got {overlap_got}"
)
print(f"  [PASS] B opt-in 200, User A appears with overlapping_themes={sorted(overlap_got)}")
# Confirm User C (High-risk) is NOT in B's candidates
assert id_c not in cand_ids, f"FAIL High-risk user C should not appear: {cand_ids}"
print("  [PASS] High-risk User C absent from B's candidate list")


# ══════════════════════════════════════════════════════════════════════════
# (c) GET /peer/candidates as User A -> User B should now appear
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (c): GET /peer/candidates as User A -> User B appears")
print(SEP)
r = _req("get", "/peer/candidates", token=tok_a, label="A get-candidates")
assert r.status_code == 200, f"FAIL expected 200 got {r.status_code}"
body = r.json()
cand_ids = [c["candidate_id"] for c in body["candidates"]]
assert id_b in cand_ids, f"FAIL User B ({id_b}) not in A's candidates: {cand_ids}"
b_entry = next(c for c in body["candidates"] if c["candidate_id"] == id_b)
print(f"  [PASS] User B appears: {b_entry}")
# Confirm fields: only candidate_id, peer_display_name, overlapping_themes
allowed_keys = {"candidate_id", "peer_display_name", "overlapping_themes"}
extra_keys = set(b_entry.keys()) - allowed_keys
assert not extra_keys, f"FAIL extra fields leaked: {extra_keys}"
print(f"  [PASS] No PII leaked — only keys: {sorted(b_entry.keys())}")
# Confirm User C absent
assert id_c not in cand_ids, f"FAIL High-risk C appears in A's candidates"
print("  [PASS] High-risk User C absent from A's candidate list")


# ══════════════════════════════════════════════════════════════════════════
# (d) Manually opt C in via DB (bypass route), give overlapping themes -> still never appears
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (d): User C (High-risk) manually opted-in via DB -> still excluded from A and B candidates")
print(SEP)
from datetime import datetime, timezone
_set_user_fields(id_c,
    available_for_matching=True,
    matching_started_at=datetime.now(timezone.utc),
)
r = _req("get", "/peer/candidates", token=tok_a, label="A get-candidates after C opted-in")
assert r.status_code == 200
body = r.json()
cand_ids = [c["candidate_id"] for c in body["candidates"]]
assert id_c not in cand_ids, f"FAIL High-risk C appeared in A's candidates: {cand_ids}"
print("  [PASS] User C (High-risk) excluded from A's candidate list even when opted-in")

r = _req("get", "/peer/candidates", token=tok_b, label="B get-candidates after C opted-in")
assert r.status_code == 200
body = r.json()
cand_ids = [c["candidate_id"] for c in body["candidates"]]
assert id_c not in cand_ids, f"FAIL High-risk C appeared in B's candidates: {cand_ids}"
print("  [PASS] User C (High-risk) excluded from B's candidate list even when opted-in")


# ══════════════════════════════════════════════════════════════════════════
# (e) High-risk user attempts POST /peer/opt-in -> 403 with crisis guidance
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (e): User C (High-risk) tries POST /peer/opt-in -> 403 + crisis guidance")
print(SEP)
# First reset C to not opted-in so we test the route itself
_set_user_fields(id_c, available_for_matching=False, matching_started_at=None)
r = _req("post", "/peer/opt-in", token=tok_c, label="C opt-in (should 403)")
assert r.status_code == 403, f"FAIL expected 403 got {r.status_code}"
body = r.json()
assert "crisis_guidance" in body, f"FAIL crisis_guidance missing from 403 body"
assert "summary" in body["crisis_guidance"], "FAIL summary missing from crisis_guidance"
assert "resources" in body["crisis_guidance"], "FAIL resources missing from crisis_guidance"
print("  [PASS] 403 received with crisis_guidance block")
# Confirm DB was NOT set
c_doc = _get_user(id_c)
assert not c_doc.get("available_for_matching"), \
    f"FAIL C's available_for_matching was set despite 403: {c_doc.get('available_for_matching')}"
print("  [PASS] User C's available_for_matching was NOT set to True in DB")


# ══════════════════════════════════════════════════════════════════════════
# (f) Bidirectional exclusion
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (f): Bidirectional exclusion — add A to B's excluded_users -> neither sees the other")
print(SEP)
# Add User A to B's excluded list via DB
_set_user_fields(id_b, excluded_users=[id_a])

# A checks candidates — B should be gone
r = _req("get", "/peer/candidates", token=tok_a, label="A get-candidates after B excludes A")
assert r.status_code == 200
body = r.json()
cand_ids = [c["candidate_id"] for c in body["candidates"]]
assert id_b not in cand_ids, f"FAIL B still appears in A's candidates after bidirectional exclusion"
print("  [PASS] A's candidate list no longer contains B (B excluded A)")

# B checks candidates — A should also be gone
r = _req("get", "/peer/candidates", token=tok_b, label="B get-candidates (A in B's excluded list)")
assert r.status_code == 200
body = r.json()
cand_ids = [c["candidate_id"] for c in body["candidates"]]
assert id_a not in cand_ids, f"FAIL A still appears in B's candidates"
print("  [PASS] B's candidate list no longer contains A")

# Restore B's excluded list for clean state
_set_user_fields(id_b, excluded_users=[])


# ══════════════════════════════════════════════════════════════════════════
# (g) Theme overlap = 0 -> no match
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (g): User D (zero theme overlap with A/B) opts in -> not shown to A or B")
print(SEP)
# Manually opt D in
_set_user_fields(id_d, available_for_matching=True,
                 matching_started_at=datetime.now(timezone.utc))

r = _req("get", "/peer/candidates", token=tok_a, label="A get-candidates (D has zero overlap)")
assert r.status_code == 200
body = r.json()
cand_ids = [c["candidate_id"] for c in body["candidates"]]
assert id_d not in cand_ids, f"FAIL D (zero overlap) appeared in A's candidates: {cand_ids}"
print("  [PASS] User D (zero overlap) does not appear in A's candidates")

r = _req("get", "/peer/candidates", token=tok_b, label="B get-candidates (D has zero overlap)")
assert r.status_code == 200
body = r.json()
cand_ids = [c["candidate_id"] for c in body["candidates"]]
assert id_d not in cand_ids, f"FAIL D (zero overlap) appeared in B's candidates: {cand_ids}"
print("  [PASS] User D (zero overlap) does not appear in B's candidates")


# ══════════════════════════════════════════════════════════════════════════
# GET /peer/candidates while NOT opted in -> 400
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (bonus): GET /peer/candidates without being opted in -> 400")
print(SEP)
_set_user_fields(id_a, available_for_matching=False)
r = _req("get", "/peer/candidates", token=tok_a, label="A get-candidates (not opted in)")
assert r.status_code == 400, f"FAIL expected 400 got {r.status_code}"
print("  [PASS] 400 returned when not opted in")

# ══════════════════════════════════════════════════════════════════════════
# POST /peer/opt-out
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (bonus): User B opts out -> B no longer appears in A's candidates")
print(SEP)
# First re-opt A in
_set_user_fields(id_a, available_for_matching=True,
                 matching_started_at=datetime.now(timezone.utc))
r = _req("post", "/peer/opt-out", token=tok_b, label="B opt-out")
assert r.status_code == 200
b_doc = _get_user(id_b)
assert not b_doc.get("available_for_matching"), "FAIL B still opted in after opt-out"
assert b_doc.get("matching_started_at") is None, "FAIL B's matching_started_at not cleared"
print("  [PASS] Opt-out 200; available_for_matching=False, matching_started_at=None in DB")

r = _req("get", "/peer/candidates", token=tok_a, label="A get-candidates after B opted out")
assert r.status_code == 200
body = r.json()
cand_ids = [c["candidate_id"] for c in body["candidates"]]
assert id_b not in cand_ids, f"FAIL B still in A's candidates after opting out"
print("  [PASS] B no longer in A's candidate list after opt-out")

# ══════════════════════════════════════════════════════════════════════════
# Idempotency: opt A in twice — matching_started_at must not change
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (bonus): Idempotency — opt A in twice, matching_started_at unchanged")
print(SEP)
a_before = _get_user(id_a)
started_before = a_before.get("matching_started_at")
r = _req("post", "/peer/opt-in", token=tok_a, label="A opt-in again (idempotent)")
assert r.status_code == 200
a_after = _get_user(id_a)
started_after = a_after.get("matching_started_at")
assert started_before == started_after, (
    f"FAIL matching_started_at changed on second opt-in: {started_before} -> {started_after}"
)
print(f"  [PASS] matching_started_at unchanged: {started_before}")


print(f"\n{SEP}")
print("ALL TESTS PASSED")
print(SEP)
