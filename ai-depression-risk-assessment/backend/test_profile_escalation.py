import os
import random
import string
import json
import requests
import time
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

BASE = 'https://ai-depression-detector.onrender.com'
suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
email_a = f'usera.esc.{suffix}@example.com'
email_b = f'userb.esc.{suffix}@example.com'
password = 'TestPass123!'

print(f"Creating User A: {email_a}")
requests.post(f'{BASE}/auth/register', json={'name': 'User A', 'email': email_a, 'password': password})
token_a = requests.post(f'{BASE}/auth/login', json={'email': email_a, 'password': password}).json().get('access_token')

print(f"Creating User B: {email_b}")
requests.post(f'{BASE}/auth/register', json={'name': 'User B', 'email': email_b, 'password': password})
token_b = requests.post(f'{BASE}/auth/login', json={'email': email_b, 'password': password}).json().get('access_token')

b_info = requests.get(f'{BASE}/auth/me', headers={'Authorization': f'Bearer {token_b}'}).json()
b_id = b_info.get('user', {}).get('id')
a_info = requests.get(f'{BASE}/auth/me', headers={'Authorization': f'Bearer {token_a}'}).json()
a_id = a_info.get('user', {}).get('id')

print("\n--- CONSENT & OPT-IN ---")
requests.post(f'{BASE}/peer/consent', headers={'Authorization': f'Bearer {token_a}'})
requests.post(f'{BASE}/peer/consent', headers={'Authorization': f'Bearer {token_b}'})

requests.post(f'{BASE}/peer/opt-in', headers={'Authorization': f'Bearer {token_a}'})
requests.post(f'{BASE}/peer/opt-in', headers={'Authorization': f'Bearer {token_b}'})

env_path = r'f:\project\ai-depression-risk-assessment\backend\.env'
mongo_uri = None
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            if k.strip() in ('MONGO_URI', 'MONGODB_URI'):
                mongo_uri = v.strip().strip('"').strip("'")
                break

client = MongoClient(mongo_uri)
db = client['mindease']

# Force User B wait time back
db.users.update_one({"_id": ObjectId(a_id)}, {"$set": {"themes": ["test-theme"]}})
db.users.update_one({"_id": ObjectId(b_id)}, {"$set": {"matching_started_at": datetime(2000, 1, 1), "themes": ["test-theme"]}})

print("\n--- MATCHING ---")
print(f"Sending request to User B ({b_id})")
req = requests.post(f'{BASE}/peer/requests', json={'receiver_id': b_id}, headers={'Authorization': f'Bearer {token_a}'})
if req.status_code != 201:
    print(f"Failed to send request: {req.text}")

requests_b = requests.get(f'{BASE}/peer/requests?type=incoming', headers={'Authorization': f'Bearer {token_b}'}).json().get('requests', [])
req_id = requests_b[0]['id']

accept = requests.post(f'{BASE}/peer/requests/{req_id}/accept', headers={'Authorization': f'Bearer {token_b}'}).json()
conv_id = accept.get('conversation_id')
print(f"Conversation established: {conv_id}")

print("\n--- ESCALATING USER A RISK LEVEL ---")
# Journal entry to trigger High risk, without crisis keywords (e.g. kill, suicide)
journal_a = "I feel utterly hopeless, overwhelmed by despair, and every day is an agonizing struggle. I have no motivation, I sleep all day, and I see absolutely no future for myself."
predict_res = requests.post(f'{BASE}/predict', json={'journal': journal_a}, headers={'Authorization': f'Bearer {token_a}'}).json()
print("Predict Response:", json.dumps(predict_res, indent=2))

user_a_doc = db.users.find_one({"_id": ObjectId(a_id)})
print(f"User A DB current_risk_level BEFORE override: {user_a_doc.get('current_risk_level')}")
if user_a_doc.get('current_risk_level') != 'High':
    print("Forcing User A to High risk to ensure test condition...")
    db.users.update_one({"_id": ObjectId(a_id)}, {"$set": {"current_risk_level": "High"}})
    user_a_doc = db.users.find_one({"_id": ObjectId(a_id)})

print(f"User A DB current_risk_level CONFIRMED: {user_a_doc.get('current_risk_level')}")

print("\n--- USER A SENDS ORDINARY MESSAGE ---")
msg1_res = requests.post(f'{BASE}/peer/conversations/{conv_id}/messages', json={'content': 'how has your day been'}, headers={'Authorization': f'Bearer {token_a}'})
print("User A message JSON Response:")
print(json.dumps(msg1_res.json(), indent=2))

print("\n--- USER B SENDS MESSAGE ---")
msg2_res = requests.post(f'{BASE}/peer/conversations/{conv_id}/messages', json={'content': 'My day has been pretty good. How about yours?'}, headers={'Authorization': f'Bearer {token_b}'})
print("User B message JSON Response:")
print(json.dumps(msg2_res.json(), indent=2))

print("\n--- POLLING MESSAGES (User A) ---")
poll_a = requests.get(f'{BASE}/peer/conversations/{conv_id}/messages', headers={'Authorization': f'Bearer {token_a}'})
print(json.dumps(poll_a.json(), indent=2))

print("\n--- POLLING MESSAGES (User B) ---")
poll_b = requests.get(f'{BASE}/peer/conversations/{conv_id}/messages', headers={'Authorization': f'Bearer {token_b}'})
print(json.dumps(poll_b.json(), indent=2))

print("\n--- DB VERIFICATION OF CONVERSATION ---")
conv_doc = db.conversations.find_one({"_id": ObjectId(conv_id)})
# Convert ObjectIds and datetimes to string for JSON printing
def default_json(obj):
    if isinstance(obj, ObjectId): return str(obj)
    if isinstance(obj, datetime): return obj.isoformat()
    raise TypeError
print(json.dumps(conv_doc, default=default_json, indent=2))
