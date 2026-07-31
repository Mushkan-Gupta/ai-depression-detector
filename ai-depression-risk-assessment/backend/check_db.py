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

print("Connecting to DB...")
client = MongoClient(mongo_uri)
db = client['mindease']
print("Connected.")

messages = list(db.messages_collection.find().sort("_id", -1).limit(5))
print("Last 5 messages:")
for m in messages:
    print(m)

convs = list(db.conversations_collection.find().sort("_id", -1).limit(5))
print("\nLast 5 conversations:")
for c in convs:
    print(c)
