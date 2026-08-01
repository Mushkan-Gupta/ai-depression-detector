import os
import json
from bson.objectid import ObjectId

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app
import db as _db

email = "mushkanguptahere@gmail.com"
with app.app_context():
    user = _db.users_collection.find_one({"email": email})
    if not user:
        print("User not found!")
        exit(1)

    user_id = str(user["_id"])
    
    print("\n--- ENDPOINTS VIA TEST CLIENT ---")
    from flask_jwt_extended import create_access_token
    access_token = create_access_token(identity=user_id)
        
    headers = {"Authorization": f"Bearer {access_token}"}
    client = app.test_client()
    
    print("\n[GET /peer/candidates]")
    res = client.get("/peer/candidates", headers=headers)
    print(res.status_code, res.get_data(as_text=True))
    
    print("\n[GET /peer/requests?type=incoming]")
    res = client.get("/peer/requests?type=incoming", headers=headers)
    print(res.status_code, res.get_data(as_text=True))
    
    print("\n[GET /peer/requests?type=sent]")
    res = client.get("/peer/requests?type=sent", headers=headers)
    print(res.status_code, res.get_data(as_text=True))
    
    print("\n[GET /peer/conversations]")
    res = client.get("/peer/conversations", headers=headers)
    print(res.status_code, res.get_data(as_text=True))
