"""
peer_requests_test.py -- End-to-end test suite for connection-request routes.

Scenarios (a) through (j) as specified.
All assertions are hard-fails via assert; output is raw HTTP status + body.
"""

import json
import sys
import requests
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import db as _db
from flask import Flask
from config import Config

BASE = "http://127.0.0.1:5000"

# ── Bootstrap DB ───────────────────────────────────────────────────────────
_app = Flask(__name__)
_app.config.from_object(Config)
_db.init_db(_app)

SEP = "=" * 70


def _req(method, path, token=None, body=None, label=""):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = getattr(requests, method)(BASE + path, headers=headers,
                                     json=body, timeout=10)
    try:
        body_out = json.dumps(resp.json(), indent=4)
    except Exception:
        body_out = resp.text
    print(f"\n  [{label}] {method.upper()} {path}")
    print(f"  HTTP {resp.status_code}")
    print(f"  {body_out}")
    return resp


def _register(email, password, name):
    r = requests.post(f"{BASE}/auth/register",
                      json={"email": email, "password": password, "name": name},
                      timeout=10)
    if r.status_code == 409:
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


def _set(user_id_str, **fields):
    _db.users_collection.update_one({"_id": ObjectId(user_id_str)}, {"$set": fields})


def _get_req(req_id_str):
    return _db.connection_requests_collection.find_one({"_id": ObjectId(req_id_str)})


def _opt_in(token):
    r = requests.post(f"{BASE}/peer/opt-in",
                      headers={"Authorization": f"Bearer {token}",
                               "Content-Type": "application/json"},
                      timeout=10)
    assert r.status_code == 200, f"opt-in failed: {r.status_code} {r.text}"


# ── Setup ──────────────────────────────────────────────────────────────────
print(SEP)
print("SETUP")
print(SEP)

tok_a, id_a = _register("cr_test_a@example.com", "TestPass1", "CR_UserA")
tok_b, id_b = _register("cr_test_b@example.com", "TestPass1", "CR_UserB")
tok_c, id_c = _register("cr_test_c@example.com", "TestPass1", "CR_UserC")  # third-party

_consent(tok_a); _consent(tok_b); _consent(tok_c)

# Wipe any leftover connection_requests from previous runs
_db.connection_requests_collection.delete_many({
    "$or": [
        {"sender_id": {"$in": [id_a, id_b, id_c]}},
        {"receiver_id": {"$in": [id_a, id_b, id_c]}},
    ]
})

# Set both A and B to valid matching state
_set(id_a,
     themes=["anxiety", "grief"],
     current_risk_level="Low",
     peer_display_name="CR-A-Anon",
     available_for_matching=True,
     matching_started_at=datetime.now(timezone.utc),
     excluded_users=[])
_set(id_b,
     themes=["anxiety", "sleep"],
     current_risk_level="Low",
     peer_display_name="CR-B-Anon",
     available_for_matching=True,
     matching_started_at=datetime.now(timezone.utc),
     excluded_users=[])
_set(id_c,
     themes=["anxiety", "grief"],
     current_risk_level="Low",
     peer_display_name="CR-C-Anon",
     available_for_matching=True,
     matching_started_at=datetime.now(timezone.utc),
     excluded_users=[])

print(f"  User A: id={id_a}  themes=[anxiety,grief]  risk=Low  opted_in=True")
print(f"  User B: id={id_b}  themes=[anxiety,sleep]  risk=Low  opted_in=True")
print(f"  User C: id={id_c}  themes=[anxiety,grief]  risk=Low  opted_in=True  (third party)")


# ══════════════════════════════════════════════════════════════════════════
# (a) A sends request to B -- valid candidates, risk snapshots captured
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (a): A sends request to B -> 201, pending, risk snapshots captured")
print(SEP)
r = _req("post", "/peer/requests", token=tok_a,
         body={"receiver_id": id_b}, label="A->B request")
assert r.status_code == 201, f"FAIL expected 201 got {r.status_code}"
body = r.json()
req_ab = body["request"]
req_ab_id = req_ab["id"]
assert req_ab["status"] == "pending", f"FAIL status={req_ab['status']}"
assert req_ab["sender_id"] == id_a
assert req_ab["receiver_id"] == id_b
assert req_ab["expires_at"] is not None
# Confirm risk snapshots in DB (NOT exposed in response)
db_doc = _get_req(req_ab_id)
assert db_doc["sender_risk_at_request"] == "Low", f"FAIL sender_risk_at_request={db_doc.get('sender_risk_at_request')}"
assert db_doc["receiver_risk_at_request"] == "Low", f"FAIL receiver_risk_at_request={db_doc.get('receiver_risk_at_request')}"
# Confirm risk levels NOT in response body
response_keys = set(req_ab.keys())
for leaked in ("sender_risk_at_request", "receiver_risk_at_request",
               "current_risk_level", "risk"):
    assert leaked not in response_keys, f"FAIL field leaked in response: {leaked}"
print(f"  [PASS] 201 pending. DB risk snapshots: sender={db_doc['sender_risk_at_request']} receiver={db_doc['receiver_risk_at_request']}")
print(f"  [PASS] Risk fields not in response body. Keys present: {sorted(response_keys)}")


# ══════════════════════════════════════════════════════════════════════════
# (b) A sends second request to B while (a) is still pending -> rejected
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (b): A sends second request to B while first is pending -> 400")
print(SEP)
r = _req("post", "/peer/requests", token=tok_a,
         body={"receiver_id": id_b}, label="A->B duplicate")
assert r.status_code == 400, f"FAIL expected 400 got {r.status_code}"
assert "already pending" in r.json().get("error", ""), f"FAIL error={r.json()}"
print("  [PASS] 400 'request already pending'")

# Also test reverse: B tries to send to A while A->B is pending
r = _req("post", "/peer/requests", token=tok_b,
         body={"receiver_id": id_a}, label="B->A (reverse, A->B pending)")
assert r.status_code == 400, f"FAIL expected 400 got {r.status_code}"
assert "already pending" in r.json().get("error", ""), f"FAIL error={r.json()}"
print("  [PASS] 400 'request already pending' for reverse direction too")


# ══════════════════════════════════════════════════════════════════════════
# (c) A sends request to themselves -> rejected
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (c): A sends request to themselves -> 400")
print(SEP)
r = _req("post", "/peer/requests", token=tok_a,
         body={"receiver_id": id_a}, label="A->A self")
assert r.status_code == 400, f"FAIL expected 400 got {r.status_code}"
assert "yourself" in r.json().get("error", ""), f"FAIL error={r.json()}"
print("  [PASS] 400 'cannot send a request to yourself'")


# ══════════════════════════════════════════════════════════════════════════
# (d) A is not a valid candidate for B (set A's risk to High) -> rejected
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (d): A's risk set to High, A tries to send NEW request to B -> 400 with specific reason")
print(SEP)
# Clean up pending A->B first so eligibility check isn't blocked by duplicate
_db.connection_requests_collection.update_one(
    {"_id": ObjectId(req_ab_id)},
    {"$set": {"status": "expired", "responded_at": datetime.now(timezone.utc)}}
)
# Make A high risk
_set(id_a, current_risk_level="High")
r = _req("post", "/peer/requests", token=tok_a,
         body={"receiver_id": id_b}, label="A(High)->B")
assert r.status_code == 400, f"FAIL expected 400 got {r.status_code}"
body = r.json()
assert body.get("error") == "not_eligible", f"FAIL error={body.get('error')}"
assert "high risk" in body.get("reason", "").lower(), f"FAIL reason={body.get('reason')}"
print(f"  [PASS] 400 not_eligible. Reason: '{body['reason']}'")
# Restore A to Low
_set(id_a, current_risk_level="Low")
# Create a fresh A->B request for remaining tests
r_new = requests.post(f"{BASE}/peer/requests",
                       headers={"Authorization": f"Bearer {tok_a}",
                                "Content-Type": "application/json"},
                       json={"receiver_id": id_b}, timeout=10)
assert r_new.status_code == 201, f"FAIL restore request: {r_new.status_code} {r_new.text}"
req_ab_id = r_new.json()["request"]["id"]
print(f"  Fresh A->B request created: id={req_ab_id}")


# ══════════════════════════════════════════════════════════════════════════
# (e) B accepts valid pending request from A -> status=accepted, responded_at set
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (e): B accepts the valid pending A->B request -> accepted")
print(SEP)
r = _req("post", f"/peer/requests/{req_ab_id}/accept", token=tok_b,
         label="B accepts A->B")
assert r.status_code == 200, f"FAIL expected 200 got {r.status_code}: {r.text}"
body = r.json()
assert body["status"] == "accepted"
assert body["responded_at"] is not None
db_doc = _get_req(req_ab_id)
assert db_doc["status"] == "accepted"
assert db_doc["responded_at"] is not None
print(f"  [PASS] 200 accepted. DB responded_at={db_doc['responded_at'].isoformat()}")


# ══════════════════════════════════════════════════════════════════════════
# (f) Fresh request, B declines -> status=declined
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (f): Fresh A->B request, B declines -> declined")
print(SEP)
r2 = requests.post(f"{BASE}/peer/requests",
                    headers={"Authorization": f"Bearer {tok_a}",
                             "Content-Type": "application/json"},
                    json={"receiver_id": id_b}, timeout=10)
assert r2.status_code == 201, f"FAIL fresh request: {r2.status_code} {r2.text}"
req_f_id = r2.json()["request"]["id"]
print(f"  Fresh A->B request: id={req_f_id}")

r = _req("post", f"/peer/requests/{req_f_id}/decline", token=tok_b,
         label="B declines A->B")
assert r.status_code == 200, f"FAIL expected 200 got {r.status_code}"
body = r.json()
assert body["status"] == "declined"
db_doc = _get_req(req_f_id)
assert db_doc["status"] == "declined"
assert db_doc.get("decline_reason") is None   # manual decline has no system reason
print(f"  [PASS] 200 declined. DB status={db_doc['status']} decline_reason={db_doc.get('decline_reason')}")


# ══════════════════════════════════════════════════════════════════════════
# (g) Fresh request, manually set expires_at to past, attempt accept -> lazy expiry
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (g): Fresh request, expires_at set to past, accept -> 410 lazy expiry")
print(SEP)
r3 = requests.post(f"{BASE}/peer/requests",
                    headers={"Authorization": f"Bearer {tok_a}",
                             "Content-Type": "application/json"},
                    json={"receiver_id": id_b}, timeout=10)
assert r3.status_code == 201, f"FAIL: {r3.status_code} {r3.text}"
req_g_id = r3.json()["request"]["id"]
print(f"  Fresh A->B request: id={req_g_id}")

# Manually expire it
_db.connection_requests_collection.update_one(
    {"_id": ObjectId(req_g_id)},
    {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(hours=1)}}
)
print("  expires_at set to 1 hour ago")

r = _req("post", f"/peer/requests/{req_g_id}/accept", token=tok_b,
         label="B accepts expired request")
assert r.status_code == 410, f"FAIL expected 410 got {r.status_code}: {r.text}"
body = r.json()
assert body.get("error") == "request_expired", f"FAIL error={body}"
db_doc = _get_req(req_g_id)
assert db_doc["status"] == "expired", f"FAIL DB status={db_doc.get('status')}"
assert db_doc.get("decline_reason") == "expired_on_access"
print(f"  [PASS] 410 request_expired. DB status=expired, decline_reason={db_doc['decline_reason']}")


# ══════════════════════════════════════════════════════════════════════════
# (h) Fresh request, receiver's risk set to High, attempt accept -> auto-declined
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (h): Fresh request, receiver (B) set to High, accept -> 409 risk escalation")
print(SEP)
r4 = requests.post(f"{BASE}/peer/requests",
                    headers={"Authorization": f"Bearer {tok_a}",
                             "Content-Type": "application/json"},
                    json={"receiver_id": id_b}, timeout=10)
assert r4.status_code == 201, f"FAIL: {r4.status_code} {r4.text}"
req_h_id = r4.json()["request"]["id"]
print(f"  Fresh A->B request: id={req_h_id}")

# Elevate B's risk to High
_set(id_b, current_risk_level="High")
print("  B's current_risk_level set to High in DB")

r = _req("post", f"/peer/requests/{req_h_id}/accept", token=tok_b,
         label="B (High-risk) accepts request")
assert r.status_code == 409, f"FAIL expected 409 got {r.status_code}: {r.text}"
body = r.json()
assert body.get("error") == "request_declined_risk_escalation", f"FAIL error={body}"
db_doc = _get_req(req_h_id)
assert db_doc["status"] == "declined", f"FAIL DB status={db_doc.get('status')}"
assert db_doc["decline_reason"] == "risk_escalation"
print(f"  [PASS] 409 risk_escalation. DB status=declined, decline_reason={db_doc['decline_reason']}")

# Restore B's risk level
_set(id_b, current_risk_level="Low")


# ══════════════════════════════════════════════════════════════════════════
# (i) Third party (C) tries to accept/decline -> 403
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (i): Third party C tries to accept/decline A->B request -> 403")
print(SEP)
r5 = requests.post(f"{BASE}/peer/requests",
                    headers={"Authorization": f"Bearer {tok_a}",
                             "Content-Type": "application/json"},
                    json={"receiver_id": id_b}, timeout=10)
assert r5.status_code == 201, f"FAIL: {r5.status_code} {r5.text}"
req_i_id = r5.json()["request"]["id"]
print(f"  Fresh A->B request: id={req_i_id}")

r = _req("post", f"/peer/requests/{req_i_id}/accept", token=tok_c,
         label="C tries to accept A->B")
assert r.status_code == 403, f"FAIL expected 403 got {r.status_code}"
print("  [PASS] 403 forbidden when C tries to accept")

r = _req("post", f"/peer/requests/{req_i_id}/decline", token=tok_c,
         label="C tries to decline A->B")
assert r.status_code == 403, f"FAIL expected 403 got {r.status_code}"
print("  [PASS] 403 forbidden when C tries to decline")

# Also try as the SENDER (A) trying to accept their own request
r = _req("post", f"/peer/requests/{req_i_id}/accept", token=tok_a,
         label="A (sender) tries to accept their own request")
assert r.status_code == 403, f"FAIL expected 403 got {r.status_code}"
print("  [PASS] 403 forbidden when sender (A) tries to accept their own request")


# ══════════════════════════════════════════════════════════════════════════
# (j) GET /peer/requests?type=incoming and ?type=sent
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("TEST (j): GET /peer/requests?type=incoming and ?type=sent")
print(SEP)

# B's incoming
r = _req("get", "/peer/requests?type=incoming", token=tok_b,
         label="B incoming requests")
assert r.status_code == 200, f"FAIL {r.status_code}"
body = r.json()
assert body["type"] == "incoming"
b_incoming_ids = {req["id"] for req in body["requests"]}
# req_i_id should be in B's incoming (it's still pending)
assert req_i_id in b_incoming_ids, f"FAIL req_i_id not in B's incoming: {b_incoming_ids}"
# Verify no risk level leaked
for req in body["requests"]:
    for leaked in ("sender_risk_at_request", "receiver_risk_at_request",
                   "current_risk_level"):
        assert leaked not in req, f"FAIL field leaked: {leaked} in {req}"
print(f"  [PASS] B incoming: {len(body['requests'])} requests. req_i_id present. No risk fields leaked.")

# A's sent
r = _req("get", "/peer/requests?type=sent", token=tok_a,
         label="A sent requests")
assert r.status_code == 200, f"FAIL {r.status_code}"
body = r.json()
assert body["type"] == "sent"
a_sent_ids = {req["id"] for req in body["requests"]}
assert req_i_id in a_sent_ids, f"FAIL req_i_id not in A's sent: {a_sent_ids}"
# All should be A's sender_id
for req in body["requests"]:
    assert req["sender_id"] == id_a, f"FAIL non-A sender in A's sent: {req['sender_id']}"
    for leaked in ("sender_risk_at_request", "receiver_risk_at_request",
                   "current_risk_level"):
        assert leaked not in req, f"FAIL field leaked: {leaked}"
print(f"  [PASS] A sent: {len(body['requests'])} requests. All sender_id=A. No risk fields leaked.")

# Confirm C has no incoming/sent from these interactions
r = _req("get", "/peer/requests?type=sent", token=tok_c,
         label="C sent requests (should be empty)")
assert r.status_code == 200
assert r.json()["requests"] == [], f"FAIL C's sent should be empty: {r.json()['requests']}"
print("  [PASS] C has no sent requests (correct isolation)")

# Confirm bad type param
r = _req("get", "/peer/requests?type=all", token=tok_a,
         label="bad type=all param")
assert r.status_code == 400
print("  [PASS] 400 for invalid type param")


print(f"\n{SEP}")
print("ALL TESTS PASSED")
print(SEP)
