import os
import random
import string
import time
import json
import requests
from pymongo import MongoClient

BASE = 'https://ai-depression-detector.onrender.com'
suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
email = f'theme.test.{suffix}@example.com'
password = 'TestPass123!'

print(f'\n--- 1. REGISTER FRESH ACCOUNT: {email} ---')
req_reg = {'name': 'Theme Test', 'email': email, 'password': password}
r_reg = requests.post(f'{BASE}/auth/register', json=req_reg, timeout=10)
print(f'Status: {r_reg.status_code}')

print(f'\n--- 2. LOGIN ---')
r_log = requests.post(f'{BASE}/auth/login', json={'email': email, 'password': password}, timeout=10)
token = r_log.json().get('access_token') or r_log.json().get('token')

print(f'\n--- 3. POST /predict WITH THEMES ---')
journal_text = 'I am completely exhausted from my job, my boss is demanding, and I have so much work and career stress.'
req_predict = {'journal': journal_text}
print(f'Request Body: {json.dumps(req_predict)}')

r_predict = requests.post(
    f'{BASE}/predict',
    json=req_predict,
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    timeout=10
)
print(f'Status: {r_predict.status_code}')
print(f'Response Body: {json.dumps(r_predict.json(), indent=2)}')

print(f'\n--- 4. MONGODB DIRECT VERIFICATION ---')
# Load MONGO_URI from .env
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

print(f'Connecting to Mongo DB... sanitized URI: {mongo_uri.split("@")[-1].split("?")[0]}')
mc = MongoClient(mongo_uri)
db = mc['mindease']

# Find User
print('\n--- USER DOCUMENT ---')
user = db.users.find_one({'email': email})
if user:
    user['_id'] = str(user['_id'])
    user['password_hash'] = '<REDACTED>'
    print(json.dumps(user, indent=2, default=str))
else:
    print('User not found!')

# Find Journal Entry
print('\n--- JOURNAL ENTRY DOCUMENT ---')
if user:
    entry = db.journal_entries.find_one({'user_id': str(user['_id'])}, sort=[('created_at', -1)])
    if entry:
        entry['_id'] = str(entry['_id'])
        print(json.dumps(entry, indent=2, default=str))
    else:
        print('Journal entry not found!')
