import os, json, datetime
from pathlib import Path
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=10000)
db = client["mindease"]

GHOST_ID   = "6a6da6242582eb7ecd09ef1a"
CONV_IDS   = ["6a6da730885a6f2ef984cb4e", "6a6dbf432ffb75b92a715e55", "6a6f18895d7af46dfa85092e"]
VALID_USERS = ["6a68c7022e7cacb19318fbd0", "6a6b556f1ca47725a6e78909", "6a3a9eb5cb6d1769d3e51585"]

SEP = "=" * 68
NOW_STR = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup_dir = Path(__file__).parent / "orphan_backups"
backup_dir.mkdir(exist_ok=True)

print(SEP)
print("PHASE A -- Pre-delete spot-check (BEFORE counts for 3 real users)")
print(SEP)
before = {}
for uid in VALID_USERS:
    before[uid] = {
        "journal_entries":          db["journal_entries"].count_documents({"user_id": uid}),
        "messages_sent":            db["messages"].count_documents({"sender_id": uid}),
        "conversations_total":      db["conversations"].count_documents({"participants": uid}),
        "connection_requests_sent": db["connection_requests"].count_documents({"sender_id": uid}),
        "connection_requests_recv": db["connection_requests"].count_documents({"receiver_id": uid}),
    }
    print("  user", uid, before[uid])
print()

print(SEP)
print("PHASE B -- Check messages in the 3 conversations")
print(SEP)
msg_docs = list(db["messages"].find({"conversation_id": {"": CONV_IDS}}))
print("  Messages found in those 3 conv_ids:", len(msg_docs))
for m in msg_docs:
    print("    _id=%s  sender=%s  conv=%s" % (m["_id"], m.get("sender_id"), m.get("conversation_id")))
print()

print(SEP)
print("PHASE C -- Check connection_requests referencing ghost user (still present?)")
print(SEP)
cr_ghost_docs = list(db["connection_requests"].find({
    "": [
        {"sender_id":   GHOST_ID},
        {"receiver_id": GHOST_ID}
    ]
}))
print("  connection_requests still referencing ghost %s: %d" % (GHOST_ID, len(cr_ghost_docs)))
for d in cr_ghost_docs:
    print("    _id=%s  sender=%s  receiver=%s  status=%s" % (
        d["_id"], d.get("sender_id"), d.get("receiver_id"), d.get("status")))
print()

print(SEP)
print("PHASE D -- Backup then delete messages for these 3 conversations")
print(SEP)
msg_backup_path = backup_dir / ("mixed_conv_messages_%s.json" % NOW_STR)
with open(msg_backup_path, "w", encoding="utf-8") as f:
    json.dump(msg_docs, f, indent=2, default=str)
print("  Messages backup:", msg_backup_path, "(%d bytes)" % msg_backup_path.stat().st_size)

if msg_docs:
    msg_ids = [d["_id"] for d in msg_docs]
    r = db["messages"].delete_many({"_id": {"": msg_ids}})
    print("  Messages deleted:", r.deleted_count)
else:
    print("  No messages to delete.")
print()

print(SEP)
print("PHASE E -- Backup then delete remaining ghost connection_requests (if any)")
print(SEP)
cr_backup_path = backup_dir / ("mixed_conv_connection_requests_%s.json" % NOW_STR)
with open(cr_backup_path, "w", encoding="utf-8") as f:
    json.dump(cr_ghost_docs, f, indent=2, default=str)
print("  CR backup:", cr_backup_path, "(%d bytes)" % cr_backup_path.stat().st_size)

if cr_ghost_docs:
    cr_ids = [d["_id"] for d in cr_ghost_docs]
    r = db["connection_requests"].delete_many({"_id": {"": cr_ids}})
    print("  connection_requests deleted:", r.deleted_count)
else:
    print("  No remaining ghost connection_requests -- already cleaned in prior pass.")
print()

print(SEP)
print("PHASE F -- Delete the 3 conversation documents themselves")
print(SEP)
conv_obj_ids = [ObjectId(c) for c in CONV_IDS]
r = db["conversations"].delete_many({"_id": {"": conv_obj_ids}})
print("  Conversations deleted:", r.deleted_count, "(expected 3)")
print()

print(SEP)
print("PHASE G -- Full orphan diagnostic (all 5 collections, should all be 0)")
print(SEP)
valid_ids = set(str(u["_id"]) for u in db["users"].find({}, {"_id": 1}))
def is_ghost(v): return v is not None and str(v) not in valid_ids

CHECKS = [
    ("journal_entries",     [("user_id", False)]),
    ("connection_requests", [("sender_id", False), ("receiver_id", False)]),
    ("conversations",       [("participants", True)]),
    ("messages",            [("sender_id", False)]),
    ("peer_reports",        [("reporter_id", False), ("reported_user_id", False)]),
]

all_zero = True
for coll_name, fields in CHECKS:
    col = db[coll_name]
    total = col.count_documents({})
    orphan_count = 0
    for doc in col.find({}):
        found = False
        if coll_name == "conversations":
            parts = doc.get("participants", [])
            parts = parts if isinstance(parts, list) else [parts]
            gh = [p for p in parts if is_ghost(p)]
            vl = [p for p in parts if not is_ghost(p)]
            if gh and not vl:
                found = True
            elif gh and vl:
                found = True  # residual mixed -- should be zero now
        else:
            for field, is_array in fields:
                raw = doc.get(field)
                if raw is None: continue
                vals = (raw if isinstance(raw, list) else [raw]) if is_array else [raw]
                if any(is_ghost(v) for v in vals):
                    found = True; break
        if found: orphan_count += 1
    ok = "[OK]" if orphan_count == 0 else "[ORPHANS REMAIN]"
    if orphan_count > 0: all_zero = False
    print("  [%s]  %s  total=%d  orphans=%d" % (ok, coll_name, total, orphan_count))

print()
print("  All collections clean:", all_zero)
print()

print(SEP)
print("PHASE H -- After spot-check for 3 real users")
print(SEP)
all_intact = True
for uid in VALID_USERS:
    after = {
        "journal_entries":          db["journal_entries"].count_documents({"user_id": uid}),
        "messages_sent":            db["messages"].count_documents({"sender_id": uid}),
        "conversations_total":      db["conversations"].count_documents({"participants": uid}),
        "connection_requests_sent": db["connection_requests"].count_documents({"sender_id": uid}),
        "connection_requests_recv": db["connection_requests"].count_documents({"receiver_id": uid}),
    }
    b = before[uid]
    mismatches = {k: (b[k], after[k]) for k in b if b[k] != after[k]}
    if mismatches: all_intact = False
    tag = "[INTACT]" if not mismatches else "[SEE DIFFS]"
    print("  user %s  %s" % (uid, tag))
    for k in b:
        flag = "  <-- CHANGED" if k in mismatches else ""
        print("    %-38s before=%-4s after=%s%s" % (k, b[k], after[k], flag))
    print()

print("  All real users intact (only conversations_total expected -1):", all_intact)
print(SEP)
