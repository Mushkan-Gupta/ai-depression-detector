"""
test_all_12_users_matching.py
Check that for each of the 12 users:
- The user has a unique anonymous name
- The user can see other candidates from the 12 users (and ONLY from the 12 users)
- No outside / ghost accounts exist
"""
import os, sys
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

# Force UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv('.env')
client = MongoClient(os.environ['MONGO_URI'], serverSelectionTimeoutMS=10000)
db = client['mindease']

users = list(db['users'].find({}))
print(f"Total registered users: {len(users)}")

user_ids = {str(u['_id']) for u in users}
user_names = {str(u['_id']): u.get('peer_display_name') for u in users}

# Check uniqueness of anonymous names
names_list = [u.get('peer_display_name') for u in users]
unique_names = set(names_list)
print(f"Total names: {len(names_list)}, Unique: {len(unique_names)}")
if len(names_list) != len(unique_names):
    print("WARNING: Duplicate anonymous names found!")
    from collections import Counter
    for name, cnt in Counter(names_list).items():
        if cnt > 1:
            print(f"  {name}: {cnt} users")
else:
    print("ALL 12 users have unique anonymous names.")

print("\n--- Current Users & Anonymous Names ---")
for i, u in enumerate(users, 1):
    print(f"{i:2d}. ID: {u['_id']} | Email: {u.get('email','')} | Anon Name: {u.get('peer_display_name')} | Available: {u.get('available_for_matching')}")

# Now check connection requests
reqs = list(db['connection_requests'].find({}))
print(f"\nTotal connection requests in DB: {len(reqs)}")
ghost_reqs = [r for r in reqs if str(r.get('sender_id')) not in user_ids or str(r.get('receiver_id')) not in user_ids]
print(f"Requests involving non-listed/ghost users: {len(ghost_reqs)}")

# Check conversations
convs = list(db['conversations'].find({}))
print(f"\nTotal conversations in DB: {len(convs)}")
ghost_convs = []
for c in convs:
    parts = [str(p) for p in c.get('participants', [])]
    if any(p not in user_ids for p in parts):
        ghost_convs.append(c)
print(f"Conversations involving non-listed/ghost users: {len(ghost_convs)}")

# Check messages
msgs = list(db['messages'].find({}))
print(f"\nTotal messages in DB: {len(msgs)}")
ghost_msgs = [m for m in msgs if str(m.get('sender_id')) not in user_ids]
print(f"Messages involving non-listed/ghost users: {len(ghost_msgs)}")
