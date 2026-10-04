import os, json, datetime
from pathlib import Path
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=10000)
db = client["mindease"]

CONV_IDS    = ["6a6da730885a6f2ef984cb4e", "6a6dbf432ffb75b92a715e55", "6a6f18895d7af46dfa85092e"]
GHOST_ID    = "6a6da6242582eb7ecd09ef1a"
VALID_USERS = ["6a68c7022e7cacb19318fbd0", "6a6b556f1ca47725a6e78909", "6a3a9eb5cb6d1769d3e51585"]

SEP     = "=" * 68
backup_dir = Path(__file__).parent / "orphan_backups"
NOW_STR = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# ── PHASE A: BEFORE spot-check ────────────────────────────────────────────────
print(SEP)
print("PHASE A -- BEFORE spot-check (3 real users)")
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

# ── PHASE B: Check messages for these 3 conv IDs ─────────────────────────────
print(SEP)
print("PHASE B -- Messages belonging to the 3 conversation IDs")
print(SEP)

# Messages field conversation_id may be stored as string or ObjectId -- check both
msg_str = list(db["messages"].find({"conversation_id": {"$in": CONV_IDS}}))
msg_obj = list(db["messages"].find({"conversation_id": {"$in": [ObjectId(c) for c in CONV_IDS]}}))
print("  Via string match   :", len(msg_str))
print("  Via ObjectId match :", len(msg_obj))
all_msgs = {str(m["_id"]): m for m in msg_str + msg_obj}
print("  Combined unique    :", len(all_msgs))
for m in all_msgs.values():
    print("    _id=%s  sender=%s  conv=%s" % (m["_id"], m.get("sender_id"), m.get("conversation_id")))
print()

# ── PHASE C: Check connection_requests referencing ghost (any remaining?) ──────
print(SEP)
print("PHASE C -- Remaining connection_requests referencing ghost %s" % GHOST_ID)
print(SEP)

cr_remain = list(db["connection_requests"].find({
    "$or": [{"sender_id": GHOST_ID}, {"receiver_id": GHOST_ID}]
}))
print("  Still present:", len(cr_remain))
for d in cr_remain:
    print("    _id=%s  sender=%s  receiver=%s  status=%s" % (
        d["_id"], d.get("sender_id"), d.get("receiver_id"), d.get("status")))
if not cr_remain:
    print("  -> Already cleaned in the prior pass. Nothing to delete here.")
print()

# ── PHASE D: Back up then delete messages (if any) ───────────────────────────
print(SEP)
print("PHASE D -- Backup + delete messages")
print(SEP)
msg_list = list(all_msgs.values())
msg_bkp = backup_dir / ("mixed_conv_messages_%s.json" % NOW_STR)
with open(msg_bkp, "w", encoding="utf-8") as f:
    json.dump(msg_list, f, indent=2, default=str)
print("  Backup:", msg_bkp, "(%d bytes)" % msg_bkp.stat().st_size)
if msg_list:
    ids = [m["_id"] for m in msg_list]
    r = db["messages"].delete_many({"_id": {"$in": ids}})
    print("  Deleted:", r.deleted_count)
else:
    print("  No messages found -- none to delete (all were ghost-sender msgs already cleaned earlier).")
print()

# ── PHASE E: Back up + delete remaining ghost CRs ────────────────────────────
print(SEP)
print("PHASE E -- Backup + delete remaining ghost connection_requests")
print(SEP)
cr_bkp = backup_dir / ("mixed_conv_connection_requests_%s.json" % NOW_STR)
with open(cr_bkp, "w", encoding="utf-8") as f:
    json.dump(cr_remain, f, indent=2, default=str)
print("  Backup:", cr_bkp, "(%d bytes)" % cr_bkp.stat().st_size)
if cr_remain:
    r = db["connection_requests"].delete_many({"_id": {"$in": [d["_id"] for d in cr_remain]}})
    print("  Deleted:", r.deleted_count)
else:
    print("  Nothing to delete.")
print()

# ── PHASE F: Delete the 3 conversation documents ─────────────────────────────
print(SEP)
print("PHASE F -- Delete the 3 conversation documents")
print(SEP)

# Confirm they exist first with ObjectId filter
conv_obj_ids = [ObjectId(c) for c in CONV_IDS]
found_before = list(db["conversations"].find({"_id": {"$in": conv_obj_ids}}))
print("  Conversations found before delete:", len(found_before))
for c in found_before:
    print("    _id=%s  participants=%s" % (c["_id"], c.get("participants")))

r = db["conversations"].delete_many({"_id": {"$in": conv_obj_ids}})
print("  Conversations deleted:", r.deleted_count, "(expected 3)")
print()

# ── PHASE G: Final full diagnostic ───────────────────────────────────────────
print(SEP)
print("PHASE G -- Final diagnostic (all 5 collections -- orphans must all be 0)")
print(SEP)

valid_ids = set(str(u["_id"]) for u in db["users"].find({}, {"_id": 1}))
def is_ghost_id(v):
    return v is not None and str(v) not in valid_ids

CHECKS = [
    ("journal_entries",     [("user_id", False)]),
    ("connection_requests", [("sender_id", False), ("receiver_id", False)]),
    ("conversations",       [("participants", True)]),
    ("messages",            [("sender_id", False)]),
    ("peer_reports",        [("reporter_id", False), ("reported_user_id", False)]),
]

all_zero = True
for coll_name, fields in CHECKS:
    col   = db[coll_name]
    total = col.count_documents({})
    orphan_count = 0
    for doc in col.find({}):
        found = False
        if coll_name == "conversations":
            parts = doc.get("participants", [])
            parts = parts if isinstance(parts, list) else [parts]
            gh = [p for p in parts if is_ghost_id(p)]
            vl = [p for p in parts if not is_ghost_id(p)]
            if gh:   # any ghost = orphan (mixed or full)
                found = True
        else:
            for field, is_array in fields:
                raw = doc.get(field)
                if raw is None:
                    continue
                vals = (raw if isinstance(raw, list) else [raw]) if is_array else [raw]
                if any(is_ghost_id(v) for v in vals):
                    found = True
                    break
        if found:
            orphan_count += 1
    ok = "[CLEAN]" if orphan_count == 0 else "[ORPHANS REMAIN]"
    if orphan_count > 0:
        all_zero = False
    print("  %s  %-25s total=%-4d  orphans=%d" % (ok, coll_name, total, orphan_count))

print()
print("  All collections fully clean:", all_zero)
print()

# ── PHASE H: AFTER spot-check ────────────────────────────────────────────────
print(SEP)
print("PHASE H -- AFTER spot-check (3 real users; conversations_total expected -1 each)")
print(SEP)
print()
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
    # conversations_total should drop by exactly 1 (the ghost-paired one); everything else must stay same
    unexpected_changes = {
        k: (b[k], after[k]) for k in b
        if b[k] != after[k] and not (k == "conversations_total" and b[k] - after[k] == 1)
    }
    expected_changes = {k: (b[k], after[k]) for k in b if b[k] != after[k] and k == "conversations_total"}
    if unexpected_changes:
        all_intact = False
    tag = "[INTACT]" if not unexpected_changes else "[UNEXPECTED CHANGE]"
    print("  user %s  %s" % (uid, tag))
    for k in b:
        note = ""
        if k in expected_changes:
            note = "  <- expected (-1, ghost conversation removed)"
        elif k in unexpected_changes:
            note = "  <- UNEXPECTED CHANGE!"
        print("    %-38s before=%-4s after=%s%s" % (k, b[k], after[k], note))
    print()

status = "YES -- all other data untouched" if all_intact else "NO -- INVESTIGATE"
print("  Other data of real users intact:", status)
print()
print(SEP)
print("  DONE")
print(SEP)
