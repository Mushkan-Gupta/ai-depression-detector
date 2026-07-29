import json
import sys
import requests
from datetime import datetime, timezone
from bson import ObjectId
import db as _db
from flask import Flask
from config import Config

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

def _cleanup(id_a, id_b):
    _db.connection_requests_collection.delete_many({"$or": [{"sender_id": {"$in": [id_a, id_b]}}, {"receiver_id": {"$in": [id_a, id_b]}}]})
    _db.conversations_collection.delete_many({"participants": {"$all": [id_a, id_b]}})
    _db.messages_collection.delete_many({"sender_id": {"$in": [id_a, id_b]}})

print("--- SETUP ---")
tok_a, id_a = _register("conv_a@example.com", "TestPass1", "ConvA")
tok_b, id_b = _register("conv_b@example.com", "TestPass1", "ConvB")
tok_c, id_c = _register("conv_c@example.com", "TestPass1", "ConvC")
_consent(tok_a); _consent(tok_b); _consent(tok_c)

_set_user(id_a, themes=["test_conv"], current_risk_level="Low", peer_display_name="Conv-A-Anon", available_for_matching=True, matching_started_at=datetime.now(timezone.utc), excluded_users=[])
_set_user(id_b, themes=["test_conv"], current_risk_level="Low", peer_display_name="Conv-B-Anon", available_for_matching=True, matching_started_at=datetime.now(timezone.utc), excluded_users=[])
_cleanup(id_a, id_b)

# --- a) B accepts A's request -> auto-create conversation
r_req = requests.post(f"{BASE}/peer/requests", headers={"Authorization": f"Bearer {tok_a}"}, json={"receiver_id": id_b})
req_id = r_req.json()["request"]["id"]
r_acc = requests.post(f"{BASE}/peer/requests/{req_id}/accept", headers={"Authorization": f"Bearer {tok_b}"})
print("\n=== a) Accept Request -> Auto-create Conversation ===")
print(f"HTTP {r_acc.status_code}")
print(json.dumps(r_acc.json(), indent=2))
conv_id = r_acc.json().get("conversation_id")
conv_doc = _db.conversations_collection.find_one({"_id": ObjectId(conv_id)})
print("DB Status:", conv_doc.get("status"))

# --- b) A sends normal message
r_msg1 = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_a}"}, json={"content": "Hello B!"})
print("\n=== b) A sends normal message ===")
print(f"HTTP {r_msg1.status_code}")
print(json.dumps(r_msg1.json(), indent=2))
msg1_id = r_msg1.json()["msg"]["_id"]

# --- c) B fetches messages (no since_id)
r_list1 = requests.get(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_b}"})
print("\n=== c) B fetches messages ===")
print(f"HTTP {r_list1.status_code}")
print(json.dumps(r_list1.json(), indent=2))

# --- d) A sends second message, B polls with since_id
r_msg2 = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_a}"}, json={"content": "Second message"})
r_list2 = requests.get(f"{BASE}/peer/conversations/{conv_id}/messages?since_id={msg1_id}", headers={"Authorization": f"Bearer {tok_b}"})
print("\n=== d) A sends second message, B polls with since_id ===")
print(f"HTTP {r_list2.status_code}")
print(json.dumps(r_list2.json(), indent=2))

# --- e) A sends crisis message
r_msg_crisis = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_a}"}, json={"content": "I might overdose tonight"})
print("\n=== e) A sends crisis message ===")
print(f"HTTP {r_msg_crisis.status_code}")
print(json.dumps(r_msg_crisis.json(), indent=2))
msg_crisis_id = r_msg_crisis.json()["msg"]["_id"]
msg_crisis_doc = _db.messages_collection.find_one({"_id": ObjectId(msg_crisis_id)})
print(f"DB crisis_flagged: {msg_crisis_doc.get('crisis_flagged')}")

r_list3 = requests.get(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_b}"})
print("\nB fetches messages -> crisis_flagged visible? (expect False/missing)")
crisis_msg_b_view = [m for m in r_list3.json()["messages"] if m["id"] == msg_crisis_id][0]
print(f"B view: {json.dumps(crisis_msg_b_view)}")

# --- f) A risk set to High -> A attempts to send -> 409 + suspended
_set_user(id_a, current_risk_level="High")
r_msg_fail_a = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_a}"}, json={"content": "Are you there?"})
print("\n=== f) A risk=High -> A attempts to send ===")
print(f"HTTP {r_msg_fail_a.status_code}")
print(json.dumps(r_msg_fail_a.json(), indent=2))
conv_doc = _db.conversations_collection.find_one({"_id": ObjectId(conv_id)})
print("DB Status:", conv_doc.get("status"), "Reason:", conv_doc.get("closed_reason"))

# --- g) B risk=High instead -> B sends -> suspends; A sends -> generic 409
_set_user(id_a, current_risk_level="Low")
_db.conversations_collection.update_one({"_id": ObjectId(conv_id)}, {"$set": {"status": "active", "closed_reason": None}})
_set_user(id_b, current_risk_level="High")
r_msg_fail_b = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_b}"}, json={"content": "Hey A"})
print("\n=== g) B risk=High -> B sends -> Suspends ===")
print(f"HTTP {r_msg_fail_b.status_code}")
# A attempts to send
r_msg_fail_a2 = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_a}"}, json={"content": "Hello?"})
print("\nA (Low risk) attempts to send into suspended conv:")
print(f"HTTP {r_msg_fail_a2.status_code}")
print(json.dumps(r_msg_fail_a2.json(), indent=2))

# --- h) B (escalated) calls GET messages -> top-level crisis guidance
print("\n=== h) B (High risk) calls GET messages ===")
r_list_h = requests.get(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_b}"})
print(f"HTTP {r_list_h.status_code}")
res_h = r_list_h.json()
print("Top-level keys:", list(res_h.keys()))
print("Has guidance?", "crisis_guidance" in res_h)
_set_user(id_b, current_risk_level="Low")

# --- i) Third-party tries to read
print("\n=== i) C tries to read/send ===")
r_list_i = requests.get(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_c}"})
print(f"Read HTTP {r_list_i.status_code}")
r_msg_i = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tok_c}"}, json={"content": "Intruder"})
print(f"Send HTTP {r_msg_i.status_code}")

# --- j) GET /peer/conversations for A
print("\n=== j) A lists conversations ===")
r_convs = requests.get(f"{BASE}/peer/conversations", headers={"Authorization": f"Bearer {tok_a}"})
print(f"HTTP {r_convs.status_code}")
print(json.dumps(r_convs.json(), indent=2))
