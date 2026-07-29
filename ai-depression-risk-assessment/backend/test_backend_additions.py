import subprocess
import requests
import json
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

print("Setting up...")
tok_a, id_a = _register("tester_a2@example.com", "TestPass1", "Tester_A")
tok_b, id_b = _register("tester_b2@example.com", "TestPass1", "Tester_B")
_consent(tok_a)
_consent(tok_b)
_db.users_collection.update_one({"_id": ObjectId(id_a)}, {"$set": {"current_risk_level": "Low", "themes": ["anxiety"]}})
_db.users_collection.update_one({"_id": ObjectId(id_b)}, {"$set": {"current_risk_level": "Low", "peer_display_name": "Tester_B_Display", "themes": ["anxiety"]}})

# Opt in
requests.post(f"{BASE}/peer/opt-in", headers={"Authorization": f"Bearer {tok_a}"})
requests.post(f"{BASE}/peer/opt-in", headers={"Authorization": f"Bearer {tok_b}"})

# Send request A -> B
requests.post(f"{BASE}/peer/requests", headers={"Authorization": f"Bearer {tok_a}"}, json={"receiver_id": id_b})

print("\n\n--- TEST (c): Normal Low-risk GET /peer/candidates ---")
subprocess.run([
    "curl", "-i", "-s", "-X", "GET", f"{BASE}/peer/candidates",
    "-H", f"Authorization: Bearer {tok_a}"
])

print("\n\n--- TEST (b): Risk escalates to High ---")
_db.users_collection.update_one({"_id": ObjectId(id_a)}, {"$set": {"current_risk_level": "High"}})

subprocess.run([
    "curl", "-i", "-s", "-X", "GET", f"{BASE}/peer/candidates",
    "-H", f"Authorization: Bearer {tok_a}"
])

user_doc = _db.users_collection.find_one({"_id": ObjectId(id_a)})
print("\n[DB Check] available_for_matching is now:", user_doc.get("available_for_matching"))

print("\n\n--- TEST (a): GET /peer/requests includes display names ---")
subprocess.run([
    "curl", "-i", "-s", "-X", "GET", f"{BASE}/peer/requests?type=sent",
    "-H", f"Authorization: Bearer {tok_a}"
])
print("\n")
