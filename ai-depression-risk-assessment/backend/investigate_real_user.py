import os
import json
from bson.objectid import ObjectId
import requests

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app
import db as _db

email = "mushkanguptahere@gmail.com"
with app.app_context():
    # app_context implicitly triggers any required setups or just accesses db variables
    user = _db.users_collection.find_one({"email": email})
    if not user:
        print("User not found!")
        exit(1)

    user_id = str(user["_id"])
    print(f"--- USER DOCUMENT ({email}) ---")
    print(json.dumps({k: v for k, v in user.items() if k not in ["password_hash", "_id", "matching_started_at", "created_at"]}, default=str, indent=2))
    print("themes:", user.get("themes"))
    print("peer_display_name:", user.get("peer_display_name"))
    print("available_for_matching:", user.get("available_for_matching"))

    print("\n--- CONNECTION REQUESTS ---")
    reqs = list(_db.connection_requests_collection.find({
        "$or": [{"sender_id": user_id}, {"receiver_id": user_id}]
    }))
    for r in reqs:
        r['_id'] = str(r['_id'])
    print(json.dumps(reqs, default=str, indent=2))

    print("\n--- CONVERSATIONS ---")
    convs = list(_db.conversations_collection.find({"participants": user_id}))
    for c in convs:
        c['_id'] = str(c['_id'])
    print(json.dumps(convs, default=str, indent=2))

    # Call endpoints directly via script
    print("\n--- ENDPOINTS ---")
    base_url = "http://127.0.0.1:5000"
    try:
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=user_id)
            
        headers = {"Authorization": f"Bearer {access_token}"}
        
        print("\n[GET /peer/candidates]")
        res = requests.get(f"{base_url}/peer/candidates", headers=headers)
        print(res.status_code, res.text)
        
        print("\n[GET /peer/requests?type=incoming]")
        res = requests.get(f"{base_url}/peer/requests?type=incoming", headers=headers)
        print(res.status_code, res.text)
        
        print("\n[GET /peer/requests?type=sent]")
        res = requests.get(f"{base_url}/peer/requests?type=sent", headers=headers)
        print(res.status_code, res.text)
        
        print("\n[GET /peer/conversations]")
        res = requests.get(f"{base_url}/peer/conversations", headers=headers)
        print(res.status_code, res.text)

    except Exception as e:
        print(f"Error calling endpoints: {e}")
