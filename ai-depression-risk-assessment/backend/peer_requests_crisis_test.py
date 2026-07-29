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

print("--- SETUP ---")
tok_a, id_a = _register("crisis_a@example.com", "TestPass1", "CrisisA")
tok_b, id_b = _register("crisis_b@example.com", "TestPass1", "CrisisB")
_consent(tok_a); _consent(tok_b)
_set_user(id_a,
     themes=["test_crisis_theme"],
     current_risk_level="Low",
     peer_display_name="CR-A-Anon",
     available_for_matching=True,
     matching_started_at=datetime.now(timezone.utc),
     excluded_users=[])
_set_user(id_b,
     themes=["test_crisis_theme"],
     current_risk_level="Low",
     peer_display_name="CR-B-Anon",
     available_for_matching=True,
     matching_started_at=datetime.now(timezone.utc),
     excluded_users=[])


print("\n\n=== a) Receiver's risk escalates -> receiver calls accept -> should have crisis guidance ===")
_cleanup(id_a, id_b)

from routes.peer_routes import _build_candidate_list
cands = _build_candidate_list(id_a)
print("Candidates for A:", cands)

r_a = requests.post(f"{BASE}/peer/requests", headers={"Authorization": f"Bearer {tok_a}"}, json={"receiver_id": id_b})
if r_a.status_code != 201:
    print("FAILED r_a:", r_a.status_code, r_a.text)
    sys.exit(1)
req_a_id = r_a.json()["request"]["id"]
_set_user(id_b, current_risk_level="High")
r_acc_a = requests.post(f"{BASE}/peer/requests/{req_a_id}/accept", headers={"Authorization": f"Bearer {tok_b}"})
print(f"HTTP {r_acc_a.status_code}")
print(json.dumps(r_acc_a.json(), indent=2))
_set_user(id_b, current_risk_level="Low")


print("\n\n=== b) Sender's risk escalates -> receiver calls accept -> should NOT have crisis guidance ===")
_cleanup(id_a, id_b)
r_b = requests.post(f"{BASE}/peer/requests", headers={"Authorization": f"Bearer {tok_a}"}, json={"receiver_id": id_b})
if r_b.status_code != 201:
    print("FAILED r_b:", r_b.status_code, r_b.text)
    sys.exit(1)
req_b_id = r_b.json()["request"]["id"]
_set_user(id_a, current_risk_level="High")
r_acc_b = requests.post(f"{BASE}/peer/requests/{req_b_id}/accept", headers={"Authorization": f"Bearer {tok_b}"})
print(f"HTTP {r_acc_b.status_code}")
print(json.dumps(r_acc_b.json(), indent=2))


print("\n\n=== c) SENDER (High risk) calls GET /peer/requests?type=sent -> should have crisis guidance at top level ===")
# A is still High risk from scenario (b)
r_get_c = requests.get(f"{BASE}/peer/requests?type=sent", headers={"Authorization": f"Bearer {tok_a}"})
print(f"HTTP {r_get_c.status_code}")
print(json.dumps(r_get_c.json(), indent=2))
_set_user(id_a, current_risk_level="Low")


print("\n\n=== d) Normal healthy GET /peer/requests -> NO crisis guidance ===")
# Both are Low risk now
r_get_d = requests.get(f"{BASE}/peer/requests?type=incoming", headers={"Authorization": f"Bearer {tok_b}"})
print(f"HTTP {r_get_d.status_code}")
print(json.dumps(r_get_d.json(), indent=2))

