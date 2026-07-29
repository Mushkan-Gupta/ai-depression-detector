import json
import requests
import db as _db
from flask import Flask
from config import Config
from datetime import datetime, timezone
from bson import ObjectId

BASE = "http://127.0.0.1:5000"

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

print("Setting up...")
tok_a, id_a = _register("g_a@example.com", "TestPass1", "G_A")
tok_b, id_b = _register("g_b@example.com", "TestPass1", "G_B")
_consent(tok_a); _consent(tok_b)
_set_user(id_a, themes=["test_g"], current_risk_level="Low", peer_display_name="G-A", available_for_matching=True, matching_started_at=datetime.now(timezone.utc), excluded_users=[])
_set_user(id_b, themes=["test_g"], current_risk_level="Low", peer_display_name="G-B", available_for_matching=True, matching_started_at=datetime.now(timezone.utc), excluded_users=[])
_db.connection_requests_collection.delete_many({"$or": [{"sender_id": {"$in": [id_a, id_b]}}, {"receiver_id": {"$in": [id_a, id_b]}}]})
_db.conversations_collection.delete_many({"participants": {"$all": [id_a, id_b]}})

# Create conversation
r_req = requests.post(f"{BASE}/peer/requests", headers={"Authorization": f"Bearer {tok_a}"}, json={"receiver_id": id_b})
req_id = r_req.json()["request"]["id"]
r_acc = requests.post(f"{BASE}/peer/requests/{req_id}/accept", headers={"Authorization": f"Bearer {tok_b}"})
conv_id = r_acc.json()["conversation_id"]

# Set B to high
_set_user(id_b, current_risk_level="High")

print("--- RAW JSON RESPONSE FOR SCENARIO (G) B POSTS MESSAGE ---")
r_msg_fail_b = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_b}"}, json={"content": "Hey A"})
print(f"HTTP {r_msg_fail_b.status_code}")
print(json.dumps(r_msg_fail_b.json(), indent=2))
