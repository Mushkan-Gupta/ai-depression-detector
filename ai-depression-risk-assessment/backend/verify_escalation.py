import os
import random
import string
import json
import requests
import time
from pymongo import MongoClient

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

# Get User B ID
b_info = requests.get(f'{BASE}/auth/me', headers={'Authorization': f'Bearer {token_b}'}).json()
b_id = b_info.get('user', {}).get('id')

print("\n--- CONSENT & OPT-IN ---")
requests.post(f'{BASE}/peer/consent', headers={'Authorization': f'Bearer {token_a}'})
requests.post(f'{BASE}/peer/consent', headers={'Authorization': f'Bearer {token_b}'})

journal_a = "My job is awful and my partner is leaving me and I cannot sleep."
requests.post(f'{BASE}/predict', json={'journal': journal_a}, headers={'Authorization': f'Bearer {token_a}'})
requests.post(f'{BASE}/predict', json={'journal': journal_a}, headers={'Authorization': f'Bearer {token_b}'})

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
from datetime import datetime
from bson import ObjectId
db.users.update_one({"_id": ObjectId(b_id)}, {"$set": {"matching_started_at": datetime(2000, 1, 1)}})

print("\n--- MATCHING ---")
print(f"Sending request to User B ({b_id})")
req = requests.post(f'{BASE}/peer/requests', json={'receiver_id': b_id}, headers={'Authorization': f'Bearer {token_a}'})
print("Request response status:", req.status_code)
print("Request response text:", req.text)

requests_b = requests.get(f'{BASE}/peer/requests?type=incoming', headers={'Authorization': f'Bearer {token_b}'}).json().get('requests', [])
if not requests_b:
    print("User B did not receive request")
    exit(1)

req_id = requests_b[0]['id']

accept = requests.post(f'{BASE}/peer/requests/{req_id}/accept', headers={'Authorization': f'Bearer {token_b}'}).json()
conv_id = accept.get('conversation_id')
print(f"Conversation established: {conv_id}")

print("\n--- ESCALATING USER A ---")
msg1_res = requests.post(f'{BASE}/peer/conversations/{conv_id}/messages', json={'content': 'I want to end it all'}, headers={'Authorization': f'Bearer {token_a}'})
print("User A sent a flagged message. JSON Response:")
print(json.dumps(msg1_res.json(), indent=2))

print("\n--- USER B SENDS MESSAGE ---")
msg2_res = requests.post(f'{BASE}/peer/conversations/{conv_id}/messages', json={'content': 'I am here for you'}, headers={'Authorization': f'Bearer {token_b}'})
print("User B sent a message. JSON Response:")
print(json.dumps(msg2_res.json(), indent=2))

print("\n--- DB VERIFICATION ---")
client2 = MongoClient(mongo_uri)
db2 = client2['mindease']
messages = list(db2.messages.find({"conversation_id": str(conv_id)}).sort("_id", 1))

print(f"Found {len(messages)} messages in DB for this conversation:")
for m in messages:
    print(f" - Sender: {m['sender_id']}, Content: {m['content']}, Flagged: {m.get('crisis_flagged')}")
