import os
import random
import string
import json
import requests
import sys

BASE = 'https://ai-depression-detector.onrender.com'
suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
email = f'theme.redeploy.{suffix}@example.com'
password = 'TestPass123!'

print(f"Creating user {email} on LIVE Render endpoint...")
req_reg = {'name': 'Theme Redeploy', 'email': email, 'password': password}
requests.post(f'{BASE}/auth/register', json=req_reg, timeout=10)
r_log = requests.post(f'{BASE}/auth/login', json={'email': email, 'password': password}, timeout=10)
token = r_log.json().get('access_token')

journal_text = "I am completely exhausted from my job, my boss is demanding, and I have so much work and career stress."
req_predict = {'journal': journal_text}

print("\n--- POST TO LIVE ENDPOINT ---")
r_predict = requests.post(
    f'{BASE}/predict',
    json=req_predict,
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    timeout=10
)
print("Response:", r_predict.json())


print("\n--- QUERY LIVE DB ---")
from pymongo import MongoClient
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
if user:
    user['_id'] = str(user['_id'])
    user['password_hash'] = '<REDACTED>'
    print(json.dumps(user, indent=2, default=str))
else:
    print("User not found in DB")

