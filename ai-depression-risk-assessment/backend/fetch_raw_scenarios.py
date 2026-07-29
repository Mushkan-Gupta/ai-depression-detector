import json
import sys
import requests
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import db as _db
from flask import Flask
from config import Config

BASE = "http://127.0.0.1:5000"

# Bootstrap DB
_app = Flask(__name__)
_app.config.from_object(Config)
_db.init_db(_app)

def _register(email, password, name):
    r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": password, "name": name})
    if r.status_code == 409:
        r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"], r.json()["user"]["id"]

def _consent(token):
    requests.post(f"{BASE}/peer/consent", headers={"Authorization": f"Bearer {token}"})

def _set_user(user_id, **fields):
    _db.users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": fields})

def _get_req(req_id):
    doc = _db.connection_requests_collection.find_one({"_id": ObjectId(req_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
        # Format datetimes nicely for printing
        for k, v in doc.items():
            if isinstance(v, datetime):
                doc[k] = v.isoformat()
    return doc

print("--- SETUP ---")
tok_a, id_a = _register("raw_a@example.com", "TestPass1", "RawA")
tok_b, id_b = _register("raw_b@example.com", "TestPass1", "RawB")
_consent(tok_a); _consent(tok_b)
_set_user(id_a, current_risk_level="Low", available_for_matching=True, matching_started_at=datetime.now(timezone.utc), themes=["anxiety"], excluded_users=[])
_set_user(id_b, current_risk_level="Low", available_for_matching=True, matching_started_at=datetime.now(timezone.utc), themes=["anxiety"], excluded_users=[])
_db.connection_requests_collection.delete_many({"$or": [{"sender_id": {"$in": [id_a, id_b]}}, {"receiver_id": {"$in": [id_a, id_b]}}]})


print("\n\n=== 1. SCENARIO (a): A sends request to B ===")
r_a = requests.post(f"{BASE}/peer/requests", headers={"Authorization": f"Bearer {tok_a}"}, json={"receiver_id": id_b})
print(f"HTTP {r_a.status_code}")
print(json.dumps(r_a.json(), indent=2))
req_a_id = r_a.json()["request"]["id"]
print("\nMongoDB Document AFTER:")
print(json.dumps(_get_req(req_a_id), indent=2))


print("\n\n=== 2. SCENARIO (d): High-risk sender ===")
_set_user(id_a, current_risk_level="High")
r_d = requests.post(f"{BASE}/peer/requests", headers={"Authorization": f"Bearer {tok_a}"}, json={"receiver_id": id_b})
print(f"HTTP {r_d.status_code}")
print(json.dumps(r_d.json(), indent=2))
_set_user(id_a, current_risk_level="Low") # Restore


print("\n\n=== 3. SCENARIO (g): Lazy Expiry ===")
_db.connection_requests_collection.delete_many({"$or": [{"sender_id": {"$in": [id_a, id_b]}}, {"receiver_id": {"$in": [id_a, id_b]}}]})
r_g = requests.post(f"{BASE}/peer/requests", headers={"Authorization": f"Bearer {tok_a}"}, json={"receiver_id": id_b})
if r_g.status_code != 201:
    print(f"FAILED TO CREATE REQ G: {r_g.status_code} {r_g.text}")
req_g_id = r_g.json()["request"]["id"]
# Manually expire
_db.connection_requests_collection.update_one({"_id": ObjectId(req_g_id)}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(hours=1)}})
print("MongoDB Document BEFORE accept attempt (manual expiry set):")
print(json.dumps(_get_req(req_g_id), indent=2))
print("\nAttempting Accept...")
r_g_acc = requests.post(f"{BASE}/peer/requests/{req_g_id}/accept", headers={"Authorization": f"Bearer {tok_b}"})
print(f"HTTP {r_g_acc.status_code}")
print(json.dumps(r_g_acc.json(), indent=2))
print("\nMongoDB Document AFTER accept attempt:")
print(json.dumps(_get_req(req_g_id), indent=2))


print("\n\n=== 4. SCENARIO (h): Receiver Risk Escalation ===")
_db.connection_requests_collection.delete_many({"$or": [{"sender_id": {"$in": [id_a, id_b]}}, {"receiver_id": {"$in": [id_a, id_b]}}]})
r_h = requests.post(f"{BASE}/peer/requests", headers={"Authorization": f"Bearer {tok_a}"}, json={"receiver_id": id_b})
req_h_id = r_h.json()["request"]["id"]
print("MongoDB Document BEFORE risk escalation:")
print(json.dumps(_get_req(req_h_id), indent=2))
# Elevate B risk
_set_user(id_b, current_risk_level="High")
print("\nAttempting Accept...")
r_h_acc = requests.post(f"{BASE}/peer/requests/{req_h_id}/accept", headers={"Authorization": f"Bearer {tok_b}"})
print(f"HTTP {r_h_acc.status_code}")
print(json.dumps(r_h_acc.json(), indent=2))
print("\nMongoDB Document AFTER accept attempt:")
print(json.dumps(_get_req(req_h_id), indent=2))
_set_user(id_b, current_risk_level="Low") # Restore
