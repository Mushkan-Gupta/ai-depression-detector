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


if __name__ == "__main__":
    run_tests()
