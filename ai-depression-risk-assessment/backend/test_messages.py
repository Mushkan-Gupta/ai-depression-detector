import sys, json, random, string, requests, time

BASE = "http://127.0.0.1:5000"

def rand_suffix(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def register_and_login(email):
    # Registration requires 'name' now
    requests.post(f"{BASE}/auth/register", json={"email": email, "password": "TestPass123!", "name": "Test User"}, timeout=10)
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "TestPass123!"}, timeout=10)
    return r.json()["access_token"], r.json()["user"]["id"]

# Setup
suf1, suf2 = rand_suffix(), rand_suffix()
email1, email2 = f"test1.{suf1}@example.com", f"test2.{suf2}@example.com"

tok1, uid1 = register_and_login(email1)
tok2, uid2 = register_and_login(email2)

# Both consent
requests.post(f"{BASE}/peer/consent", json={"consent": True}, headers=auth_headers(tok1))
requests.post(f"{BASE}/peer/consent", json={"consent": True}, headers=auth_headers(tok2))

# We need to manually add themes to DB for both users so they match
from pymongo import MongoClient
import os
env_path = os.path.join(os.path.dirname(__file__), ".env")
mongo_uri = None
with open(env_path) as f:
    for line in f:
        if "MONGO_URI=" in line:
            mongo_uri = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
from bson import ObjectId
mc = MongoClient(mongo_uri)
db = mc["mindease"]
unique_theme = f"test_theme_{rand_suffix()}"
res1 = db.users.update_one({"_id": ObjectId(uid1)}, {"$set": {"themes": [unique_theme], "current_risk_level": "Low", "available_for_matching": False}})
res2 = db.users.update_one({"_id": ObjectId(uid2)}, {"$set": {"themes": [unique_theme], "current_risk_level": "Low", "available_for_matching": False}})
print("Updates:", res1.modified_count, res2.modified_count, "Theme:", unique_theme)

# Both opt in
r_opt1 = requests.post(f"{BASE}/peer/opt-in", headers=auth_headers(tok1))
r_opt2 = requests.post(f"{BASE}/peer/opt-in", headers=auth_headers(tok2))
print("Opt1:", r_opt1.status_code, "Opt2:", r_opt2.status_code)

# Request & Accept
print(f"\n>>> POST /peer/requests (User 1 -> User 2)")
r_req = requests.post(f"{BASE}/peer/requests", json={"receiver_id": uid2}, headers=auth_headers(tok1))
print("HTTP", r_req.status_code, r_req.json())
time.sleep(1)

reqs = requests.get(f"{BASE}/peer/requests?type=incoming", headers=auth_headers(tok2)).json()
print("User 2 incoming requests:", reqs)
req_id = [r["id"] for r in reqs.get("requests", []) if r["status"] == "pending"][0]
acc_res = requests.post(f"{BASE}/peer/requests/{req_id}/accept", headers=auth_headers(tok2)).json()
conv_id = acc_res["conversation_id"]

print(f"\n--- CONVERSATION CREATED: {conv_id} ---")

# User 1 sends message
print(f"\n>>> POST /peer/conversations/{conv_id}/messages (User 1)")
msg_payload = {"content": "Hello this is a test message!"}
print("    body:", json.dumps(msg_payload))
r_send = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", json=msg_payload, headers=auth_headers(tok1))
print("HTTP", r_send.status_code)
print(json.dumps(r_send.json(), indent=2))
msg_id = r_send.json().get("msg", {}).get("_id")

# User 2 polls messages without since_id
print(f"\n>>> GET /peer/conversations/{conv_id}/messages (User 2 - NO since_id)")
r_poll1 = requests.get(f"{BASE}/peer/conversations/{conv_id}/messages", headers=auth_headers(tok2))
print("HTTP", r_poll1.status_code)
print(json.dumps(r_poll1.json(), indent=2))

# User 2 polls messages with since_id
print(f"\n>>> GET /peer/conversations/{conv_id}/messages?since_id={msg_id} (User 2 - WITH since_id)")
r_poll2 = requests.get(f"{BASE}/peer/conversations/{conv_id}/messages?since_id={msg_id}", headers=auth_headers(tok2))
print("HTTP", r_poll2.status_code)
print(json.dumps(r_poll2.json(), indent=2))

# Risk escalation test
print("\n--- SETTING USER 1 RISK TO HIGH ---")
db.users.update_one({"_id": ObjectId(uid1)}, {"$set": {"current_risk_level": "High"}})
time.sleep(1)

print(f"\n>>> POST /peer/conversations/{conv_id}/messages (User 1 - High Risk)")
r_escalation = requests.post(f"{BASE}/peer/conversations/{conv_id}/messages", json={"content": "This should fail due to escalation"}, headers=auth_headers(tok1))
print("HTTP", r_escalation.status_code)
print(json.dumps(r_escalation.json(), indent=2))


