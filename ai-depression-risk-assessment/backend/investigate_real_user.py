"""
Investigation script for mushkanguptahere@gmail.com
Uses import db as _db pattern consistent with the rest of this codebase.
Calls live Render endpoints using a generated JWT.
"""

import json
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app to get flask context (needed for JWT generation)
from app import app
import db as _db

EMAIL = "mushkanguptahere@gmail.com"
LIVE_BASE = "https://ai-depression-detector.onrender.com"

def j(obj):
    return json.dumps(obj, default=str, indent=2)

with app.app_context():
    # ── 1. USER DOCUMENT ──────────────────────────────────────────────────────
    user = _db.users_collection.find_one({"email": EMAIL})
    if not user:
        print(f"ERROR: user {EMAIL} not found in DB")
        sys.exit(1)

    user_id = str(user["_id"])

    print("=" * 70)
    print(f"USER DOCUMENT ({EMAIL})")
    print("=" * 70)
    safe = {k: v for k, v in user.items() if k not in ("password_hash", "_id")}
    safe["_id"] = user_id
    print(j(safe))

    print()
    print(f"  available_for_matching : {user.get('available_for_matching')}")
    print(f"  peer_display_name      : {user.get('peer_display_name')}")
    print(f"  themes                 : {user.get('themes')}")
    print(f"  current_risk_level     : {user.get('current_risk_level')}")

    # ── 2. CONNECTION REQUESTS ────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("CONNECTION REQUESTS (sender or receiver = this user)")
    print("=" * 70)
    reqs = list(_db.connection_requests_collection.find({
        "$or": [{"sender_id": user_id}, {"receiver_id": user_id}]
    }))
    for r in reqs:
        r["_id"] = str(r["_id"])
    print(j(reqs))

    # ── 3. CONVERSATIONS ──────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("CONVERSATIONS (participants contains this user)")
    print("=" * 70)
    convs = list(_db.conversations_collection.find({"participants": user_id}))
    for c in convs:
        c["_id"] = str(c["_id"])
    print(j(convs))

    # ── 4. LIVE API CALLS VIA JWT ─────────────────────────────────────────────
    print()
    print("=" * 70)
    print("LIVE API CALLS (Render)")
    print("=" * 70)

    from flask_jwt_extended import create_access_token
    token = create_access_token(identity=user_id)
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/peer/candidates",
        "/peer/requests?type=incoming",
        "/peer/requests?type=sent",
        "/peer/conversations",
    ]

    for ep in endpoints:
        url = f"{LIVE_BASE}{ep}"
        print()
        print(f"[GET {ep}]")
        try:
            res = requests.get(url, headers=headers, timeout=30)
            print(f"  Status: {res.status_code}")
            try:
                print(j(res.json()))
            except Exception:
                print(f"  Raw: {res.text[:500]}")
        except Exception as e:
            print(f"  ERROR: {e}")
