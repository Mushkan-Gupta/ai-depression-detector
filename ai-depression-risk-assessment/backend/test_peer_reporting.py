"""
test_peer_reporting.py — Test Suite for Peer Reporting & Auto-Exclusion
-----------------------------------------------------------------------
Verifies:
 1. Single report creation & status check
 2. Duplicate report prevention (idempotency via unique index)
 3. Boundary check: 2 distinct reports do NOT trigger exclusion; candidate matching query STILL includes user D
 4. 3rd distinct report triggers auto-exclusion:
    - DB field available_for_matching becomes False
    - matching_started_at becomes None
    - End-to-end candidate match query (GET /peer/candidates) NO LONGER includes user D
"""

import os
import sys
from datetime import datetime, timezone

from bson import ObjectId
from flask_jwt_extended import create_access_token

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as flask_app
import db as _db

def run_tests():
    print("=" * 70)
    print("PEER REPORTING & AUTO-EXCLUSION TEST SUITE")
    print("=" * 70)

    # Setup test client and rebind DB handles to mindease_test database
    flask_app.config["TESTING"] = True
    _db._db = _db._client["mindease_test"]
    _db.users_collection = _db._db["users"]
    _db.journal_entries_collection = _db._db["journal_entries"]
    _db.connection_requests_collection = _db._db["connection_requests"]
    _db.conversations_collection = _db._db["conversations"]
    _db.messages_collection = _db._db["messages"]
    _db.peer_reports_collection = _db._db["peer_reports"]

    # Hard safety check
    if _db._db.name != "mindease_test":
        print(f"[FATAL] Safety check failed! Connected to {_db._db.name} instead of mindease_test", file=sys.stderr)
        sys.exit(1)

    # Clean test DB collections first, then build indexes cleanly
    _db.users_collection.delete_many({})
    _db.conversations_collection.delete_many({})
    _db.peer_reports_collection.delete_many({})
    _db.connection_requests_collection.delete_many({})

    _db._ensure_indexes()

    client = flask_app.test_client()

    # 1. Create 5 test users: A, B, C, D (target), E (evaluator for matching candidate queries)
    now = datetime.now(timezone.utc)
    users = {
        "A": {"email": "user_a_rep@example.com", "peer_display_name": "Reporter-A"},
        "B": {"email": "user_b_rep@example.com", "peer_display_name": "Reporter-B"},
        "C": {"email": "user_c_rep@example.com", "peer_display_name": "Reporter-C"},
        "D": {"email": "user_d_target@example.com", "peer_display_name": "Target-D"},
        "E": {"email": "user_e_eval@example.com", "peer_display_name": "Evaluator-E"},
    }

    user_ids = {}
    tokens = {}

    for key, data in users.items():
        doc = {
            "email": data["email"],
            "password_hash": "testpass",
            "peer_display_name": data["peer_display_name"],
            "peer_consent": {"accepted": True, "accepted_at": now, "version": "1.0"},
            "themes": ["Work & Career Stress"],
            "current_risk_level": "Low",
            "available_for_matching": True,
            "matching_started_at": now,
            "excluded_users": [],
        }
        res = _db.users_collection.insert_one(doc)
        uid = str(res.inserted_id)
        user_ids[key] = uid
        with flask_app.app_context():
            tokens[key] = create_access_token(identity=uid)

    print(f"Created 5 test users: {list(user_ids.keys())}")

    # 2. Create 3 distinct active conversations with user D: Conv 1 (A&D), Conv 2 (B&D), Conv 3 (C&D)
    conv1 = str(_db.conversations_collection.insert_one({
        "participants": [user_ids["A"], user_ids["D"]],
        "status": "active",
        "created_at": now,
    }).inserted_id)

    conv2 = str(_db.conversations_collection.insert_one({
        "participants": [user_ids["B"], user_ids["D"]],
        "status": "active",
        "created_at": now,
    }).inserted_id)

    conv3 = str(_db.conversations_collection.insert_one({
        "participants": [user_ids["C"], user_ids["D"]],
        "status": "active",
        "created_at": now,
    }).inserted_id)

    print(f"Created 3 conversations: Conv1 ({conv1[:6]}), Conv2 ({conv2[:6]}), Conv3 ({conv3[:6]})")

    # ── TEST 1: First Report by User A against D in Conv 1 ──────────────────────
    print("\n--- TEST 1: User A reports D in Conv 1 ---")
    headers_a = {"Authorization": f"Bearer {tokens['A']}"}
    res1 = client.post(f"/peer/conversations/{conv1}/report", headers=headers_a, json={
        "reason": "harassment",
        "details": "Inappropriate messages"
    })

    assert res1.status_code == 201, f"Expected 201, got {res1.status_code}: {res1.get_data(as_text=True)}"
    data1 = res1.get_json()
    assert data1.get("already_reported") is False, f"Expected already_reported=False, got {data1}"
    print(f"  [PASS] Report submitted (201): {data1.get('message')}")

    # Check report status GET endpoint
    st1 = client.get(f"/peer/conversations/{conv1}/report-status", headers=headers_a).get_json()
    assert st1.get("reported") is True, f"Expected reported=True, got {st1}"
    print(f"  [PASS] GET report-status returned reported=True")

    # Check DB state for User D
    d_doc = _db.users_collection.find_one({"_id": ObjectId(user_ids["D"])})
    assert d_doc.get("available_for_matching") is True, "User D should STILL be available_for_matching=True after 1 report"
    reporters = _db.peer_reports_collection.distinct("reporter_id", {"reported_user_id": user_ids["D"]})
    assert len(reporters) == 1, f"Expected 1 distinct reporter, got {len(reporters)}"
    print(f"  [PASS] DB check: 1 report logged, available_for_matching STILL True")

    # ── TEST 2: Duplicate Report by User A against D in Conv 1 ──────────────────
    print("\n--- TEST 2: Duplicate report by User A in Conv 1 ---")
    res2 = client.post(f"/peer/conversations/{conv1}/report", headers=headers_a, json={
        "reason": "harassment",
        "details": "Duplicate report attempt"
    })

    assert res2.status_code == 200, f"Expected 200 on duplicate, got {res2.status_code}: {res2.get_data(as_text=True)}"
    data2 = res2.get_json()
    assert data2.get("already_reported") is True, f"Expected already_reported=True, got {data2}"
    print(f"  [PASS] Duplicate caught gracefully (200): {data2.get('message')}")

    # Verify count is still 1
    reporters = _db.peer_reports_collection.distinct("reporter_id", {"reported_user_id": user_ids["D"]})
    assert len(reporters) == 1, f"Expected 1 distinct reporter after duplicate attempt, got {len(reporters)}"
    total_docs = _db.peer_reports_collection.count_documents({"reported_user_id": user_ids["D"]})
    assert total_docs == 1, f"Expected 1 report doc in collection, got {total_docs}"
    print(f"  [PASS] DB check: 1 report doc in DB, no duplicate inserted")

    # ── TEST 3: 2nd Report (User B in Conv 2) + Boundary Check ──────────────────
    print("\n--- TEST 3: User B reports D in Conv 2 (2nd distinct reporter) ---")
    headers_b = {"Authorization": f"Bearer {tokens['B']}"}
    res3 = client.post(f"/peer/conversations/{conv2}/report", headers=headers_b, json={
        "reason": "spam"
    })

    assert res3.status_code == 201, f"Expected 201, got {res3.status_code}"
    reporters = _db.peer_reports_collection.distinct("reporter_id", {"reported_user_id": user_ids["D"]})
    assert len(reporters) == 2, f"Expected 2 distinct reporters, got {len(reporters)}"

    d_doc = _db.users_collection.find_one({"_id": ObjectId(user_ids["D"])})
    assert d_doc.get("available_for_matching") is True, "User D should STILL be available_for_matching=True after 2 reports"
    print(f"  [PASS] 2 distinct reports logged; available_for_matching STILL True")

    # BOUNDARY CHECK: Call GET /peer/candidates as User E
    headers_e = {"Authorization": f"Bearer {tokens['E']}"}
    cands_res1 = client.get("/peer/candidates", headers=headers_e)
    assert cands_res1.status_code == 200, f"Candidates query failed: {cands_res1.status_code}"
    cand_ids = [c["candidate_id"] for c in cands_res1.get_json().get("candidates", [])]
    assert user_ids["D"] in cand_ids, f"Boundary check failed: User D should STILL appear in candidates after 2 reports! Got {cand_ids}"
    print(f"  [PASS] Boundary check: User D STILL appears in GET /peer/candidates (candidate count = {len(cand_ids)})")

    # ── TEST 4: 3rd Report (User C in Conv 3) + Auto-Exclusion Verification ────
    print("\n--- TEST 4: User C reports D in Conv 3 (3rd distinct reporter) ---")
    headers_c = {"Authorization": f"Bearer {tokens['C']}"}
    res4 = client.post(f"/peer/conversations/{conv3}/report", headers=headers_c, json={
        "reason": "safety_concern"
    })

    assert res4.status_code == 201, f"Expected 201, got {res4.status_code}"
    reporters = _db.peer_reports_collection.distinct("reporter_id", {"reported_user_id": user_ids["D"]})
    assert len(reporters) == 3, f"Expected 3 distinct reporters, got {len(reporters)}"

    # Check DB state for User D after 3rd report
    d_doc_after = _db.users_collection.find_one({"_id": ObjectId(user_ids["D"])})
    assert d_doc_after.get("available_for_matching") is False, "User D available_for_matching MUST be False after 3 distinct reports"
    assert d_doc_after.get("matching_started_at") is None, "User D matching_started_at MUST be set to None"
    print(f"  [PASS] DB check: available_for_matching=False and matching_started_at=None in DB")

    # END-TO-END QUERY VERIFICATION: Call GET /peer/candidates as User E
    cands_res2 = client.get("/peer/candidates", headers=headers_e)
    assert cands_res2.status_code == 200, f"Candidates query failed: {cands_res2.status_code}"
    cand_ids_after = [c["candidate_id"] for c in cands_res2.get_json().get("candidates", [])]
    assert user_ids["D"] not in cand_ids_after, f"End-to-end exclusion failed: User D MUST NOT appear in candidates after 3 reports! Got {cand_ids_after}"
    print(f"  [PASS] End-to-end query check: User D NO LONGER appears in GET /peer/candidates (candidate list excludes D)")

    print("\n" + "=" * 70)
    print("ALL PEER REPORTING & AUTO-EXCLUSION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


def run_block_tests():
    """
    TEST 5 — report-only path (block=False): conversation stays open, no exclusion.
    TEST 6 — report+block path (block=True): conversation closes, reported user
              added to reporter's excluded_users, but a 3rd user is unaffected
              (confirming one-directional exclusion).
    """
    print("\n" + "=" * 70)
    print("BLOCK-ON-REPORT TEST SUITE (TESTS 5 & 6)")
    print("=" * 70)

    # Ensure we are on the test DB (run_tests() already switched, but be safe)
    flask_app.config["TESTING"] = True
    _db._db = _db._client["mindease_test"]
    _db.users_collection = _db._db["users"]
    _db.conversations_collection = _db._db["conversations"]
    _db.peer_reports_collection = _db._db["peer_reports"]
    _db.connection_requests_collection = _db._db["connection_requests"]

    if _db._db.name != "mindease_test":
        print(f"[FATAL] Safety check failed! Connected to {_db._db.name}", file=sys.stderr)
        sys.exit(1)

    client = flask_app.test_client()
    now = datetime.now(timezone.utc)
    SHARED_THEME = ["Grief & Loss"]

    # ── Create 4 fresh users for isolation ──────────────────────────────────
    block_users = {
        "F": "user_f_block@example.com",
        "G": "user_g_block@example.com",
        "H": "user_h_blocker@example.com",
        "I": "user_i_blocked@example.com",
        "J": "user_j_observer@example.com",   # 3rd party — should still see I
    }
    b_ids = {}
    b_tokens = {}
    for key, email in block_users.items():
        # Remove any leftover doc from a previous run
        _db.users_collection.delete_one({"email": email})
        doc = {
            "email": email,
            "password_hash": "testpass",
            "peer_display_name": f"Block-{key}",
            "peer_consent": {"accepted": True, "accepted_at": now, "version": "1.0"},
            "themes": SHARED_THEME,
            "current_risk_level": "Low",
            "available_for_matching": True,
            "matching_started_at": now,
            "excluded_users": [],
        }
        res = _db.users_collection.insert_one(doc)
        uid = str(res.inserted_id)
        b_ids[key] = uid
        with flask_app.app_context():
            b_tokens[key] = create_access_token(identity=uid)

    print(f"Created 5 block-test users: {list(b_ids.keys())}")

    # ── TEST 5: report-only (block=False) ────────────────────────────────────
    print("\n--- TEST 5: report-only path (block=False) — conv stays open ---")

    conv_fg = str(_db.conversations_collection.insert_one({
        "participants": [b_ids["F"], b_ids["G"]],
        "status": "active",
        "closed_reason": None,
        "created_at": now,
    }).inserted_id)

    res5 = client.post(
        f"/peer/conversations/{conv_fg}/report",
        headers={"Authorization": f"Bearer {b_tokens['F']}"},
        json={"reason": "spam", "block": False},
    )
    assert res5.status_code == 201, f"TEST 5 expected 201, got {res5.status_code}: {res5.get_data(as_text=True)}"
    data5 = res5.get_json()
    assert data5.get("blocked") is False, f"TEST 5: expected blocked=False in response, got {data5}"
    print(f"  [PASS] Response: blocked=False")

    # Conversation must still be active
    conv_fg_doc = _db.conversations_collection.find_one({"_id": ObjectId(conv_fg)})
    assert conv_fg_doc["status"] == "active", f"TEST 5: conversation should remain 'active', got {conv_fg_doc['status']}"
    print(f"  [PASS] DB: conversation status still 'active'")

    # F's excluded_users must NOT contain G
    f_doc = _db.users_collection.find_one({"_id": ObjectId(b_ids["F"])})
    assert b_ids["G"] not in [str(x) for x in f_doc.get("excluded_users", [])], \
        f"TEST 5: G must not be in F's excluded_users, got {f_doc.get('excluded_users')}"
    print(f"  [PASS] DB: G not in F's excluded_users")

    # G should still appear in F's candidate list
    cands5 = client.get("/peer/candidates", headers={"Authorization": f"Bearer {b_tokens['F']}"})
    assert cands5.status_code == 200, f"TEST 5: candidates query failed: {cands5.status_code}"
    cand_ids5 = [c["candidate_id"] for c in cands5.get_json().get("candidates", [])]
    assert b_ids["G"] in cand_ids5, \
        f"TEST 5: G should STILL appear in F's candidate list after report-only, got {cand_ids5}"
    print(f"  [PASS] GET /peer/candidates: G still appears for F")

    # ── TEST 6: report+block (block=True) ────────────────────────────────────
    print("\n--- TEST 6: report+block path (block=True) ---")

    conv_hi = str(_db.conversations_collection.insert_one({
        "participants": [b_ids["H"], b_ids["I"]],
        "status": "active",
        "closed_reason": None,
        "created_at": now,
    }).inserted_id)

    res6 = client.post(
        f"/peer/conversations/{conv_hi}/report",
        headers={"Authorization": f"Bearer {b_tokens['H']}"},
        json={"reason": "harassment", "block": True},
    )
    assert res6.status_code == 201, f"TEST 6 expected 201, got {res6.status_code}: {res6.get_data(as_text=True)}"
    data6 = res6.get_json()
    assert data6.get("blocked") is True, f"TEST 6: expected blocked=True in response, got {data6}"
    print(f"  [PASS] Response: blocked=True")

    # Conversation must be closed
    conv_hi_doc = _db.conversations_collection.find_one({"_id": ObjectId(conv_hi)})
    assert conv_hi_doc["status"] == "closed", \
        f"TEST 6: conversation should be 'closed', got {conv_hi_doc['status']}"
    assert conv_hi_doc.get("closed_reason") == "user_blocked", \
        f"TEST 6: closed_reason should be 'user_blocked', got {conv_hi_doc.get('closed_reason')}"
    print(f"  [PASS] DB: conversation status='closed', closed_reason='user_blocked'")

    # H's excluded_users must contain I
    h_doc = _db.users_collection.find_one({"_id": ObjectId(b_ids["H"])})
    h_excluded = [str(x) for x in h_doc.get("excluded_users", [])]
    assert b_ids["I"] in h_excluded, \
        f"TEST 6: I must be in H's excluded_users, got {h_excluded}"
    print(f"  [PASS] DB: I is in H's excluded_users")

    # I must NOT appear in H's candidate list (one-directional block)
    cands6_h = client.get("/peer/candidates", headers={"Authorization": f"Bearer {b_tokens['H']}"})
    assert cands6_h.status_code == 200, f"TEST 6: H's candidates query failed: {cands6_h.status_code}"
    cand_ids6_h = [c["candidate_id"] for c in cands6_h.get_json().get("candidates", [])]
    assert b_ids["I"] not in cand_ids6_h, \
        f"TEST 6: I must NOT appear in H's candidate list after block, got {cand_ids6_h}"
    print(f"  [PASS] GET /peer/candidates (H): I no longer appears for H")

    # I's own excluded_users must NOT contain H (block is one-directional)
    i_doc = _db.users_collection.find_one({"_id": ObjectId(b_ids["I"])})
    i_excluded = [str(x) for x in i_doc.get("excluded_users", [])]
    assert b_ids["H"] not in i_excluded, \
        f"TEST 6: H must NOT be in I's excluded_users (one-directional), got {i_excluded}"
    print(f"  [PASS] DB: H not in I's excluded_users (block is one-directional)")

    # J (third user, same theme, no history with I) must still see I as a candidate
    cands6_j = client.get("/peer/candidates", headers={"Authorization": f"Bearer {b_tokens['J']}"})
    assert cands6_j.status_code == 200, f"TEST 6: J's candidates query failed: {cands6_j.status_code}"
    cand_ids6_j = [c["candidate_id"] for c in cands6_j.get_json().get("candidates", [])]
    assert b_ids["I"] in cand_ids6_j, \
        f"TEST 6: I MUST still appear in J's candidate list (exclusion is one-directional), got {cand_ids6_j}"
    print(f"  [PASS] GET /peer/candidates (J): I still appears for unrelated user J")

    print("\n" + "=" * 70)
    print("ALL BLOCK-ON-REPORT TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
    run_block_tests()
