import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv('.env')
client = MongoClient(os.environ['MONGO_URI'], serverSelectionTimeoutMS=10000)
db = client['mindease']

users = list(db['users'].find({}, {
    'name': 1, 'email': 1, 'peer_display_name': 1,
    'available_for_matching': 1, 'peer_consent': 1,
    'themes': 1, 'current_risk_level': 1
}))
print(f'Total users: {len(users)}')
print()
for u in users:
    print(f"  Name              : {u.get('name','')}")
    print(f"  Email             : {u.get('email','')}")
    print(f"  peer_display_name : {u.get('peer_display_name', '(NONE)')}")
    print(f"  available         : {u.get('available_for_matching', False)}")
    print(f"  current_risk      : {u.get('current_risk_level', '(none)')}")
    consent = u.get('peer_consent', {})
    print(f"  peer_consent      : accepted={consent.get('accepted',False)} v={consent.get('version','')}")
    print(f"  themes            : {u.get('themes', [])}")
    print()
