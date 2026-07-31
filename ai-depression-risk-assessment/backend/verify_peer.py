import os
import random
import string
import json
import requests
from pymongo import MongoClient

BASE = 'https://ai-depression-detector.onrender.com'
suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
email_a = f'usera.{suffix}@example.com'
email_b = f'userb.{suffix}@example.com'
password = 'TestPass123!'

print(f"Creating User A: {email_a}")
requests.post(f'{BASE}/auth/register', json={'name': 'User A', 'email': email_a, 'password': password})
token_a = requests.post(f'{BASE}/auth/login', json={'email': email_a, 'password': password}).json().get('access_token')

print(f"Creating User B: {email_b}")
requests.post(f'{BASE}/auth/register', json={'name': 'User B', 'email': email_b, 'password': password})
token_b = requests.post(f'{BASE}/auth/login', json={'email': email_b, 'password': password}).json().get('access_token')

print("\n--- CONSENT ---")
requests.post(f'{BASE}/peer/consent', headers={'Authorization': f'Bearer {token_a}'})
requests.post(f'{BASE}/peer/consent', headers={'Authorization': f'Bearer {token_b}'})

print("\n--- PREDICT (THEMES) ---")
journal_text = "I am completely exhausted from my job, my boss is demanding, and I have so much work and career stress."
requests.post(f'{BASE}/predict', json={'journal': journal_text}, headers={'Authorization': f'Bearer {token_a}'})
requests.post(f'{BASE}/predict', json={'journal': journal_text}, headers={'Authorization': f'Bearer {token_b}'})

print("\n--- OPT-IN ---")
requests.post(f'{BASE}/peer/opt-in', headers={'Authorization': f'Bearer {token_a}'})
requests.post(f'{BASE}/peer/opt-in', headers={'Authorization': f'Bearer {token_b}'})

print("\n--- GET /peer/candidates (USER A) ---")
candidates_a = requests.get(f'{BASE}/peer/candidates', headers={'Authorization': f'Bearer {token_a}'}).json()
print("Raw JSON Response:")
print(json.dumps(candidates_a, indent=2))

# Database fallback
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
user_b_doc = db.users.find_one({'email': email_b})
user_b_id = str(user_b_doc['_id']) if user_b_doc else None

b_found = False
for c in candidates_a:
    if c.get('candidate_id') == user_b_id:
        b_found = True
        break

if not b_found:
    print("\n[!] User B did NOT appear in the candidates list! Querying database...")
    user_a_doc = db.users.find_one({'email': email_a})
    
    print("\n--- USER A DB INFO ---")
    if user_a_doc:
        print(f"themes: {user_a_doc.get('themes')}")
        print(f"current_risk_level: {user_a_doc.get('current_risk_level')}")
        print(f"matching_started_at: {user_a_doc.get('matching_started_at')}")
        
    print("\n--- USER B DB INFO ---")
    if user_b_doc:
        print(f"themes: {user_b_doc.get('themes')}")
        print(f"current_risk_level: {user_b_doc.get('current_risk_level')}")
        print(f"matching_started_at: {user_b_doc.get('matching_started_at')}")
else:
    print("\n[+] Success! User B appeared in User A's candidates list.")
