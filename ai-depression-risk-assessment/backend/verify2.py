import os
import random
import string
import time
import json
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE = 'https://ai-depression-detector.onrender.com'
suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
email = f'verify2.{suffix}@example.com'
password = 'TestPass123!'

req_reg = {'name': 'Verify Two', 'email': email, 'password': password}
requests.post(f'{BASE}/auth/register', json=req_reg, timeout=10)
r_log = requests.post(f'{BASE}/auth/login', json={'email': email, 'password': password}, timeout=10)
token = r_log.json().get('access_token') or r_log.json().get('token')

journal_text = 'Just testing if the database writes are working or silently failing.'
req_predict = {'journal': journal_text}
print("=== REQUEST BODY ===")
print(json.dumps(req_predict))

r_predict = requests.post(
    f'{BASE}/predict',
    json=req_predict,
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    timeout=10
)
print("=== RESPONSE BODY ===")
print(json.dumps(r_predict.json(), indent=2))

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

mc = MongoClient(mongo_uri)
db = mc['mindease']

user = db.users.find_one({'email': email})
print("=== MONGO USER ID ===")
print(str(user['_id']) if user else "None")

print("=== MONGO JOURNAL_ENTRIES.FIND_ONE ===")
if user:
    entry = db.journal_entries.find_one({'user_id': str(user['_id'])}, sort=[('created_at', -1)])
    if entry:
        entry_id_str = str(entry['_id'])
        # re-fetch to prove exact query by ObjectId works
        exact_entry = db.journal_entries.find_one({"_id": ObjectId(entry_id_str)})
        if exact_entry:
            exact_entry['_id'] = str(exact_entry['_id'])
            print(json.dumps(exact_entry, indent=2, default=str))
        else:
            print("None")
    else:
        print("None")
else:
    print("None")

print("=== MONGO JOURNAL_ENTRIES.COUNT_DOCUMENTS ===")
count = db.journal_entries.count_documents({})
print(count)

print("=== LIVE DB TARGET (SANITIZED) ===")
print(mongo_uri.split("@")[-1].split("?")[0])
