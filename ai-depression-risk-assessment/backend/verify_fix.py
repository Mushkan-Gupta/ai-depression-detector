"""
Verify script:
1. POST /peer/opt-in for mushkanguptahere@gmail.com → confirm 200
2. GET /peer/candidates → confirm 200 (not 500) with JSON payload
"""

import json, sys, os, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
import db as _db

EMAIL = "mushkanguptahere@gmail.com"
LIVE  = "https://ai-depression-detector.onrender.com"

def j(o): return json.dumps(o, default=str, indent=2)

with app.app_context():
    user = _db.users_collection.find_one({"email": EMAIL})
    if not user:
        print("ERROR: user not found"); sys.exit(1)
    user_id = str(user["_id"])

    from flask_jwt_extended import create_access_token
    token = create_access_token(identity=user_id)
    H = {"Authorization": f"Bearer {token}"}

    print("=" * 60)
    print("POST /peer/opt-in")
    print("=" * 60)
    r = requests.post(f"{LIVE}/peer/opt-in", headers=H, timeout=30)
    print(f"Status: {r.status_code}")
    try:    print(j(r.json()))
    except: print(r.text[:400])

    print()
    print("=" * 60)
    print("GET /peer/candidates")
    print("=" * 60)
    r = requests.get(f"{LIVE}/peer/candidates", headers=H, timeout=30)
    print(f"Status: {r.status_code}")
    try:    print(j(r.json()))
    except: print(r.text[:400])

    print()
    print("=" * 60)
    print("DB check: available_for_matching after opt-in call")
    print("=" * 60)
    u2 = _db.users_collection.find_one({"email": EMAIL}, {"available_for_matching": 1, "peer_display_name": 1})
    print(f"  available_for_matching : {u2.get('available_for_matching')}")
    print(f"  peer_display_name      : {u2.get('peer_display_name')}")
