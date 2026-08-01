import json
import os
from bson import json_util
from app import app
import db as _db
from flask_jwt_extended import create_access_token

def dump(obj):
    return json.loads(json_util.dumps(obj))

def redact(doc):
    if not doc: return doc
    if 'password_hash' in doc:
        doc['password_hash'] = '[REDACTED]'
    return doc

emails = ['mushkanguptahere@gmail.com', 'gmushkan49@gmail.com']

with app.app_context():
    # 4. Users
    users = list(_db.users_collection.find({"email": {"$in": emails}}))
    print("--- USERS ---")
    for u in users:
        print(json.dumps(redact(dump(u)), indent=2))
        
    user_ids = {u['email']: str(u['_id']) for u in users}
    
    # 5. Journal Entries
    print("\n--- JOURNAL ENTRIES ---")
    for email, uid in user_ids.items():
        print(f"User: {email}")
        entries = list(_db.journal_entries_collection.find({"user_id": uid}).sort("created_at", -1).limit(3))
        for e in entries:
            print(json.dumps(dump(e), indent=2))
            
    # 6. Connection Requests
    print("\n--- CONNECTION REQUESTS ---")
    if len(user_ids) == 2:
        u1 = user_ids.get(emails[0])
        u2 = user_ids.get(emails[1])
        if u1 and u2:
            reqs = list(_db.connection_requests_collection.find({
                "$or": [
                    {"sender_id": u1, "receiver_id": u2},
                    {"sender_id": u2, "receiver_id": u1}
                ]
            }))
            for r in reqs:
                print(json.dumps(dump(r), indent=2))
            
    # 7. Call API
    print("\n--- API RESPONSES ---")
    with app.test_client() as client:
        for email, uid in user_ids.items():
            access_token = create_access_token(identity=uid)
            headers = {"Authorization": f"Bearer {access_token}"}
            res = client.get("/peer/candidates", headers=headers)
            print(f"Response for {email}:")
            print(res.status_code)
            print(res.get_data(as_text=True))
