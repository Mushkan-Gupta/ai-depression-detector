"""
diagnose_orphans.py -- READ-ONLY orphan diagnostic
---------------------------------------------------
Connects to MongoDB Atlas, collects all valid user _id values,
then scans each child collection for documents whose user-reference
fields point to a user_id that no longer exists in users_collection.

NO documents are modified or deleted. This is purely diagnostic.
"""

import os, sys, json
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

# -- Load env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    sys.exit("FATAL: MONGO_URI not found in .env")

# -- Connect
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client["mindease"]
print("[DB] Connected OK\n")

# -- Step 1: Collect all valid user _ids
users_col = db["users"]
valid_user_ids = set(str(u["_id"]) for u in users_col.find({}, {"_id": 1}))
total_users = len(valid_user_ids)
print("=== users_collection ===")
print(f"  Total users: {total_users}")
print(f"  Sample IDs (first 5): {list(valid_user_ids)[:5]}\n")


def is_orphan(value):
    if value is None:
        return False
    return str(value) not in valid_user_ids


def stringify_doc(doc):
    def default(o):
        if isinstance(o, ObjectId):
            return str(o)
        return repr(o)
    return json.dumps(doc, indent=2, default=default)


# -- Step 2: Per-collection checks
CHECKS = [
    ("journal_entries",      [("user_id", False)]),
    ("connection_requests",  [("sender_id", False), ("receiver_id", False)]),
    ("conversations",        [("participants", True)]),
    ("messages",             [("sender_id", False)]),
    ("peer_reports",         [("reporter_id", False), ("reported_user_id", False)]),
]

SEP = "=" * 60

for coll_name, fields in CHECKS:
    col = db[coll_name]
    total_docs = col.count_documents({})
    orphan_docs = []

    for doc in col.find({}):
        for field, is_array in fields:
            raw = doc.get(field)
            if raw is None:
                continue
            if is_array:
                values = raw if isinstance(raw, list) else [raw]
                bad = [v for v in values if is_orphan(v)]
                if bad:
                    orphan_docs.append((doc, field, bad))
                    break
            else:
                if is_orphan(raw):
                    orphan_docs.append((doc, field, raw))
                    break

    print(SEP)
    print(f"COLLECTION: {coll_name}")
    print(f"  Total documents   : {total_docs}")
    print(f"  Orphaned documents: {len(orphan_docs)}")

    if orphan_docs:
        print("\n  --- Example orphaned documents (up to 3) ---")
        for i, (doc, field, bad_val) in enumerate(orphan_docs[:3]):
            print(f"\n  [Example {i+1}]  offending field='{field}', bad_value={bad_val}")
            print("  " + stringify_doc(doc).replace("\n", "\n  "))
    else:
        print("  OK No orphans found.")
    print()

print(SEP)
print("Diagnosis complete. NO data was modified.")
