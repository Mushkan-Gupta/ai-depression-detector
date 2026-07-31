import requests
import json
import uuid
import sys
import os
from pymongo import MongoClient
import urllib.parse
from datetime import datetime, timezone

# Add backend directory to sys.path so we can import config
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
from config import Config

client = MongoClient(Config.MONGO_URI)
db = client['mindease']

BASE_URL = "http://localhost:5000"

def log_step(step_name, response=None):
    print(f"\n{'='*80}\n{step_name}\n{'-'*80}")
    if response is not None:
        print(f"Status Code: {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)

def register_user(name, email, password):
    res = requests.post(f"{BASE_URL}/auth/register", json={"name": name, "email": email, "password": password})
    assert res.status_code == 201, f"Failed to register {name}: {res.text}"
    token = res.json()['access_token']
    user_id = res.json()['user']['id']
    return token, user_id

def set_themes(user_id, themes):
    from bson import ObjectId
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"themes": themes}})

def set_risk(token, phrase):
    res = requests.post(f"{BASE_URL}/predict", headers={"Authorization": f"Bearer {token}"}, json={"journal": phrase})
    return res

print("STARTING E2E VERIFICATION")
db.users.update_many({}, {"$set": {"available_for_matching": False}})

users = [
    {"name": "Nora", "themes": ["anxiety", "loneliness"], "phrase": "I feel happy and grateful today."},
    {"name": "Owen", "themes": ["anxiety", "grief"], "phrase": "I feel happy and grateful today."},
    {"name": "Priya", "themes": ["work_stress"], "phrase": "Sometimes I just want to sleep in on Saturdays and do nothing."},
    {"name": "Quinn", "themes": ["anxiety", "loneliness"], "phrase": "I had a great day, I am so happy and grateful, yet I want to end it all."},
    {"name": "Rosa", "themes": ["loneliness"], "phrase": "I feel happy and grateful today."}
]

tokens = {}
uids = {}
display_names = {}

# Registration and setup
for u in users:
    email = f"{u['name'].lower()}_{uuid.uuid4().hex[:6]}@example.com"
    token, uid = register_user(u['name'], email, "TestPass1!")
    tokens[u['name']] = token
    uids[u['name']] = uid
    set_themes(uid, u['themes'])
    # Hit predict to set risk level
    set_risk(token, u['phrase'])

# 1. All 5 register and call POST /peer/consent.
for u in users:
    name = u['name']
    token = tokens[name]
    res = requests.post(f"{BASE_URL}/peer/consent", headers={"Authorization": f"Bearer {token}"}, json={"accepted": True})
    log_step(f"1. {name} POST /peer/consent", res)
    display_names[name] = res.json().get('peer_display_name')

# 2. All 5 attempt POST /peer/opt-in.
for u in users:
    name = u['name']
    token = tokens[name]
    res = requests.post(f"{BASE_URL}/peer/opt-in", headers={"Authorization": f"Bearer {token}"})
    log_step(f"2. {name} POST /peer/opt-in", res)

# 3. Nora calls GET /peer/candidates.
res = requests.get(f"{BASE_URL}/peer/candidates", headers={"Authorization": f"Bearer {tokens['Nora']}"})
log_step("3. Nora GET /peer/candidates", res)

# 4. Nora sends a connection request to Owen.
# Find Owen's ID (we have it in uids)
res = requests.post(f"{BASE_URL}/peer/requests", headers={"Authorization": f"Bearer {tokens['Nora']}"}, json={"receiver_id": uids['Owen']})
log_step("4. Nora POST /peer/requests to Owen", res)
req_id = res.json().get('request', {}).get('id')

# 5. Owen calls GET /peer/requests?type=incoming and accepts it.
res = requests.get(f"{BASE_URL}/peer/requests?type=incoming", headers={"Authorization": f"Bearer {tokens['Owen']}"})
log_step("5a. Owen GET /peer/requests?type=incoming", res)

req_id_to_accept = req_id if req_id else res.json().get('requests', [])[0]['id']
res = requests.post(f"{BASE_URL}/peer/requests/{req_id_to_accept}/accept", headers={"Authorization": f"Bearer {tokens['Owen']}"})
log_step("5b. Owen POST /peer/requests/.../accept", res)
conv_id = res.json().get('conversation_id')

# 6. Nora and Owen's conversation
# a. Owen sends message
res = requests.post(f"{BASE_URL}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tokens['Owen']}"}, json={"content": "Hey, nice to connect with someone who gets it."})
log_step("6a. Owen sends message", res)

# b. Nora polls messages
res = requests.get(f"{BASE_URL}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tokens['Nora']}"})
log_step("6b. Nora GET /peer/conversations/.../messages", res)

# c. Nora replies with high risk keyword
res = requests.post(f"{BASE_URL}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tokens['Nora']}"}, json={"content": "Yeah, I'm glad too. Just dealing with some thoughts of suicide recently."})
log_step("6c. Nora sends HIGH RISK message", res)

# Owen checks messages (should not see crisis guidance)
res = requests.get(f"{BASE_URL}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tokens['Owen']}"})
log_step("6c (follow-up). Owen GET messages (should NOT see crisis flagged)", res)

# 7. Escalate Owen's risk to High
res = set_risk(tokens['Owen'], "I am so excited for the future, everything is going great, but I think I will overdose tonight.")
log_step("7. Escalate Owen to High via /predict", res)
# Check DB
from bson import ObjectId
owen_doc = db.users.find_one({"_id": ObjectId(uids['Owen'])})
print(f"Owen's current_risk_level in DB: {owen_doc.get('current_risk_level')}")

# 8. Owen attempts to send another message
res = requests.post(f"{BASE_URL}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tokens['Owen']}"}, json={"content": "Are you still there?"})
log_step("8. Owen sends message after escalation (should be 409)", res)

conv_doc = db.conversations.find_one({"_id": ObjectId(conv_id)})
print(f"Conversation status in DB: {conv_doc.get('status')}")

# 9. Nora attempts to send message to suspended conversation
res = requests.post(f"{BASE_URL}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tokens['Nora']}"}, json={"content": "I'm here!"})
log_step("9. Nora sends message to suspended conversation", res)

# 10. Nora sends request to Rosa, Rosa declines
res = requests.post(f"{BASE_URL}/peer/requests", headers={"Authorization": f"Bearer {tokens['Nora']}"}, json={"receiver_id": uids['Rosa']})
req_rosa_id = res.json().get('request', {}).get('id')
log_step("10a. Nora sends request to Rosa", res)

res = requests.post(f"{BASE_URL}/peer/requests/{req_rosa_id}/decline", headers={"Authorization": f"Bearer {tokens['Rosa']}"})
log_step("10b. Rosa declines request", res)

req_rosa_doc = db.connection_requests.find_one({"_id": ObjectId(req_rosa_id)})
print(f"Request status in DB: {req_rosa_doc.get('status')}")

# 11. Third party (Priya) attempts to GET and POST
res = requests.get(f"{BASE_URL}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tokens['Priya']}"})
log_step("11a. Priya GET conversation", res)

res = requests.post(f"{BASE_URL}/peer/conversations/{conv_id}/messages", headers={"Authorization": f"Bearer {tokens['Priya']}"}, json={"content": "Hello?"})
log_step("11b. Priya POST message", res)

# 12. GET /peer/conversations for Nora
res = requests.get(f"{BASE_URL}/peer/conversations", headers={"Authorization": f"Bearer {tokens['Nora']}"})
log_step("12. Nora GET /peer/conversations", res)

print("\nE2E VERIFICATION COMPLETE")
