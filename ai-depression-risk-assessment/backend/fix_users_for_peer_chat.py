"""
fix_users_for_peer_chat.py
---------------------------
Fixes all users so they:
1. Have a unique anonymous peer_display_name
2. Have peer_consent accepted (v1.0)
3. Are available_for_matching = True
4. Have at least one theme (so they appear in candidate lists)
5. Have current_risk_level = "Low" (so they're not blocked by High-risk filter)

Run once from the backend directory:
    python fix_users_for_peer_chat.py
"""

import os
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

load_dotenv('.env')
client = MongoClient(os.environ['MONGO_URI'], serverSelectionTimeoutMS=10000)
db = client['mindease']

CONSENT_VERSION = "1.0"

# Full word pool (matches peer_routes.py)
_DISPLAY_NAME_WORDS = [
    "Aspen", "Birch", "Cedar", "Clover", "Coral",
    "Creek", "Dew", "Drift", "Dusk", "Fern",
    "Field", "Fjord", "Flint", "Fog", "Forest",
    "Glade", "Glen", "Grotto", "Grove", "Harbor",
    "Hazel", "Heather", "Inlet", "Iris", "Jasper",
    "Lake", "Lark", "Laurel", "Linden", "Lotus",
    "Maple", "Marsh", "Meadow", "Mesa", "Mist",
    "Moon", "Moss", "Opal", "Pebble", "Pine",
    "Pond", "Reef", "Ridge", "River", "Robin",
    "Sage", "Shore", "Stone", "Stream", "Vale",
]

DEFAULT_THEMES = [
    "Social & Loneliness",
    "Future Outlook",
    "Anxiety & Fear",
    "Work & Career Stress",
    "Sleep & Energy",
]

now = datetime.now(timezone.utc)

# Load all users
users = list(db['users'].find({}))
print(f"Found {len(users)} users\n")

# Track which names are already in use (to guarantee uniqueness)
used_names = set()
for u in users:
    name = u.get('peer_display_name')
    if name:
        used_names.add(name)

# Remaining words available for assignment
remaining_words = [w for w in _DISPLAY_NAME_WORDS
                   if f"Anonymous {w}" not in used_names]
random.shuffle(remaining_words)

word_iter = iter(remaining_words)


def next_unique_name():
    try:
        word = next(word_iter)
    except StopIteration:
        # Fallback: use a number suffix
        word = f"User{random.randint(100, 999)}"
    return f"Anonymous {word}"


changes_made = 0

for u in users:
    uid = u['_id']
    email = u.get('email', '')
    updates = {}
    log_lines = []

    # 1. Assign unique peer_display_name if missing
    existing_name = u.get('peer_display_name')
    if not existing_name:
        new_name = next_unique_name()
        used_names.add(new_name)
        updates['peer_display_name'] = new_name
        log_lines.append(f"  + peer_display_name = {new_name}")

    # 2. Ensure peer_consent is set and accepted
    consent = u.get('peer_consent', {})
    if not consent.get('accepted') or consent.get('version') != CONSENT_VERSION:
        updates['peer_consent'] = {
            'accepted': True,
            'accepted_at': now,
            'version': CONSENT_VERSION,
        }
        log_lines.append("  + peer_consent = accepted v1.0")

    # 3. Set available_for_matching = True
    if not u.get('available_for_matching'):
        updates['available_for_matching'] = True
        updates['matching_started_at'] = now
        log_lines.append("  + available_for_matching = True")

    # 4. Ensure themes list is non-empty
    themes = u.get('themes', [])
    if not themes:
        updates['themes'] = DEFAULT_THEMES
        log_lines.append(f"  + themes = {DEFAULT_THEMES}")

    # 5. Set current_risk_level = Low if not set (so they appear in candidates)
    if not u.get('current_risk_level'):
        updates['current_risk_level'] = 'Low'
        log_lines.append("  + current_risk_level = Low")

    if updates:
        db['users'].update_one({'_id': uid}, {'$set': updates})
        changes_made += 1
        print(f"Updated: {u.get('name','')} <{email}>")
        for line in log_lines:
            print(line)
        print()
    else:
        print(f"OK (no changes): {u.get('name','')} <{email}> -> {u.get('peer_display_name')}")

print(f"\nDone. {changes_made} user(s) updated.")

# ── Final verification ─────────────────────────────────────────────────────
print("\n" + "="*65)
print("FINAL STATE")
print("="*65)
users_after = list(db['users'].find({}, {
    'name': 1, 'email': 1, 'peer_display_name': 1,
    'available_for_matching': 1, 'peer_consent': 1,
    'themes': 1, 'current_risk_level': 1
}))

# Check uniqueness
all_names = [u.get('peer_display_name') for u in users_after]
unique_names = set(all_names)
has_duplicates = len(all_names) != len(unique_names)

for i, u in enumerate(users_after, 1):
    status = "Y" if u.get('available_for_matching') else "N"
    print(f"  {i:2}. [{status}] {u.get('peer_display_name','(NONE)'):25}  {u.get('name',''):20}  {u.get('email','')}")

print()
if has_duplicates:
    print("WARNING: Duplicate anonymous names detected!")
    from collections import Counter
    c = Counter(all_names)
    for name, count in c.items():
        if count > 1:
            print(f"  DUPLICATE: {name} (x{count})")
else:
    print("All anonymous names are unique.")

available_count = sum(1 for u in users_after if u.get('available_for_matching'))
print(f"\n{available_count}/{len(users_after)} users available for matching.")
