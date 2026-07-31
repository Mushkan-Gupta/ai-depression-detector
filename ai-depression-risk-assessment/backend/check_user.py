import os
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
user = db.users.find_one({'email': 'userb.x6cp9n@example.com'})
print(f"User B ID: {str(user['_id']) if user else 'Not found'}")
