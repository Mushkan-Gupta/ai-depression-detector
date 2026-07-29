import subprocess
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

print("Setting up...")
tok_a, id_a = _register("curl_a@example.com", "TestPass1", "Curl_A")

conv = _db.conversations_collection.find_one({})
conv_id = str(conv["_id"]) if conv else "6a6997b4941a83cd7de156d6"
_db.conversations_collection.update_one({"_id": ObjectId(conv_id)}, {"$addToSet": {"participants": id_a}})
_consent(tok_a)

print("\n--- TEST 1: POST with malformed conv_id ---")
subprocess.run([
    "curl", "-i", "-s", "-X", "POST", f"{BASE}/peer/conversations/not-a-real-id/messages",
    "-H", f"Authorization: Bearer {tok_a}",
    "-H", "Content-Type: application/json",
    "-d", '{"content": "hello"}'
])

print("\n\n--- TEST 2: GET with malformed conv_id ---")
subprocess.run([
    "curl", "-i", "-s", "-X", "GET", f"{BASE}/peer/conversations/not-a-real-id/messages",
    "-H", f"Authorization: Bearer {tok_a}"
])

print("\n\n--- TEST 3: GET with valid conv_id but malformed since_id ---")
subprocess.run([
    "curl", "-i", "-s", "-X", "GET", f"{BASE}/peer/conversations/{conv_id}/messages?since_id=not-a-real-id",
    "-H", f"Authorization: Bearer {tok_a}"
])
print("\n")
