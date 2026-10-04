"""
orphan_cleanup.py  — Safe Orphan Cleanup with Backup & Spot-Check
==================================================================
Steps executed:
  1. Collect valid user IDs + per-collection BEFORE counts (spot-check anchors).
  2. Classify every orphaned document:
       - fully_orphaned : ALL referenced users are ghosts  → will be deleted
       - mixed          : >=1 valid participant + >=1 ghost → flagged, NOT deleted
  3. Report mixed conversations separately.
  4. Write JSON backup per collection (one file each) to orphan_backups/.
  5. Confirm every backup file exists on disk.
  6. Delete only fully-orphaned documents.
  7. Re-run full diagnostic — orphan counts should all be 0.
  8. Spot-check 3 real users — before/after counts must be identical.
  9. Write master cleanup_summary_*.json.

Run from the backend directory:
    python orphan_cleanup.py
"""

import os, sys, json, datetime
from pathlib import Path
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

# Force UTF-8 output so Unicode check-marks don't crash on Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 0. Bootstrap ─────────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    sys.exit("FATAL: MONGO_URI not found in .env")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client["mindease"]
print("[DB] Connected to MongoDB Atlas OK\n")

BACKUP_DIR = Path(__file__).parent / "orphan_backups"
BACKUP_DIR.mkdir(exist_ok=True)

NOW_STR = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SEP = "=" * 68


def bson_default(o):
    if isinstance(o, ObjectId):
        return str(o)
    if isinstance(o, (datetime.datetime, datetime.date)):
        return o.isoformat()
    return repr(o)


def write_backup(filename: str, docs: list) -> Path:
    filepath = BACKUP_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, default=bson_default)
    return filepath


# ── 1. Collect valid user IDs ─────────────────────────────────────────────────
print(SEP)
print("STEP 1  — Valid users + BEFORE spot-check counts")
print(SEP)

users_col = db["users"]
all_users = list(users_col.find({}, {"_id": 1, "email": 1, "name": 1}))
valid_user_ids = set(str(u["_id"]) for u in all_users)
total_users = len(valid_user_ids)

print(f"\n  Valid users in 'users' collection : {total_users}")
print(f"  Sample IDs (first 5): {list(valid_user_ids)[:5]}\n")


def is_ghost(value):
    if value is None:
        return False
    return str(value) not in valid_user_ids


SPOT_USERS = list(valid_user_ids)[:3]

before_spot = {}
for uid in SPOT_USERS:
    before_spot[uid] = {
        "journal_entries":           db["journal_entries"].count_documents({"user_id": uid}),
        "messages_sent":             db["messages"].count_documents({"sender_id": uid}),
        "conversations":             db["conversations"].count_documents({"participants": uid}),
        "connection_requests_sent":  db["connection_requests"].count_documents({"sender_id": uid}),
        "connection_requests_recv":  db["connection_requests"].count_documents({"receiver_id": uid}),
    }

print("  BEFORE counts for 3 real users (spot-check anchors):")
for uid, counts in before_spot.items():
    print(f"    {uid}: {counts}")
print()


# ── 2. Per-collection orphan classification ────────────────────────────────────
CHECKS = [
    ("journal_entries",     [("user_id",           False)]),
    ("connection_requests", [("sender_id",          False), ("receiver_id", False)]),
    ("conversations",       [("participants",       True)]),
    ("messages",            [("sender_id",          False)]),
    ("peer_reports",        [("reporter_id",        False), ("reported_user_id", False)]),
]

fully_orphaned = {}   # coll_name -> [doc, ...]
mixed_convs    = []   # conversations with >=1 valid + >=1 ghost participant

print(SEP)
print("STEP 2  — Orphan classification (fully-orphaned vs mixed)")
print(SEP)

for coll_name, fields in CHECKS:
    col = db[coll_name]
    total_docs = col.count_documents({})
    full_orphan_docs = []

    for doc in col.find({}):
        is_orphaned = False

        if coll_name == "conversations":
            raw = doc.get("participants", [])
            participants = raw if isinstance(raw, list) else [raw]
            ghost_parts = [p for p in participants if is_ghost(p)]
            valid_parts = [p for p in participants if not is_ghost(p)]

            if ghost_parts and valid_parts:
                mixed_convs.append(doc)
                continue
            elif ghost_parts and not valid_parts:
                is_orphaned = True
        else:
            for field, is_array in fields:
                raw = doc.get(field)
                if raw is None:
                    continue
                if is_array:
                    values = raw if isinstance(raw, list) else [raw]
                    if any(is_ghost(v) for v in values):
                        is_orphaned = True
                        break
                else:
                    if is_ghost(raw):
                        is_orphaned = True
                        break

        if is_orphaned:
            full_orphan_docs.append(doc)

    fully_orphaned[coll_name] = full_orphan_docs

    mixed_note = f"  | mixed(flagged)={len(mixed_convs)}" if coll_name == "conversations" else ""
    print(f"\n  [{coll_name}]")
    print(f"    Total docs     : {total_docs}")
    print(f"    Fully orphaned : {len(full_orphan_docs)}{mixed_note}")

print()


# ── 3. Report mixed conversations ─────────────────────────────────────────────
print(SEP)
print("STEP 3  — Mixed conversations (valid user + ghost) — FLAGGED, NOT deleted")
print(SEP)

if mixed_convs:
    print(f"\n  *** {len(mixed_convs)} MIXED conversation(s) found. These will NOT be deleted. ***")
    print("      Backup → mixed_conversations_MANUAL_REVIEW.json\n")
    for i, c in enumerate(mixed_convs, 1):
        raw_parts = c.get("participants", [])
        valid_p   = [str(p) for p in raw_parts if not is_ghost(p)]
        ghost_p   = [str(p) for p in raw_parts if is_ghost(p)]
        print(f"  [{i}] _id={c['_id']}")
        print(f"       valid_participants : {valid_p}")
        print(f"       ghost_participants : {ghost_p}")
else:
    print("\n  No mixed conversations found — all orphaned conversations are fully ghosted.\n")

mixed_backup_path = write_backup(
    f"mixed_conversations_MANUAL_REVIEW_{NOW_STR}.json",
    mixed_convs
)
print(f"\n  Mixed backup → {mixed_backup_path}  ({mixed_backup_path.stat().st_size} bytes)")


# ── 4. Write per-collection backups ───────────────────────────────────────────
print()
print(SEP)
print("STEP 4  — Writing JSON backups of fully-orphaned documents")
print(SEP)

backup_paths = {}
total_to_delete = 0

for coll_name, docs in fully_orphaned.items():
    if docs:
        fname = f"{coll_name}_orphans_{NOW_STR}.json"
        path  = write_backup(fname, docs)
        backup_paths[coll_name] = str(path)
        total_to_delete += len(docs)
        print(f"\n  [{coll_name}]  {len(docs)} docs  →  {path}")
    else:
        backup_paths[coll_name] = None
        print(f"\n  [{coll_name}]  0 docs  (no backup needed)")

print(f"\n  Total documents to be deleted: {total_to_delete}")


# ── 5. Confirm backups on disk ────────────────────────────────────────────────
print()
print("  Verifying backup files exist on disk …")
all_backups_ok = True
for coll_name, path_str in backup_paths.items():
    if path_str is not None:
        p = Path(path_str)
        if not p.exists():
            print(f"  ✗  MISSING backup for [{coll_name}]: {p}")
            all_backups_ok = False
        else:
            print(f"  ✓  [{coll_name}]  {p.stat().st_size:>8} bytes  →  {p}")

if not all_backups_ok:
    sys.exit("\nABORT: One or more backup files are missing. Deletion cancelled for safety.")

print("\n  All backups confirmed on disk. Proceeding with deletion …\n")


# ── 6. Delete fully-orphaned documents ────────────────────────────────────────
print(SEP)
print("STEP 5  — Deleting fully-orphaned documents")
print(SEP)

deletion_counts = {}

for coll_name, docs in fully_orphaned.items():
    if not docs:
        deletion_counts[coll_name] = 0
        print(f"\n  [{coll_name}]  0 to delete — skipped.")
        continue

    col    = db[coll_name]
    ids    = [doc["_id"] for doc in docs]
    result = col.delete_many({"_id": {"$in": ids}})
    deleted = result.deleted_count
    deletion_counts[coll_name] = deleted

    ok = "✓" if deleted == len(docs) else "⚠"
    print(f"\n  [{coll_name}]  {ok}  requested={len(docs)}  actually_deleted={deleted}")

print()


# ── 7. Post-deletion diagnostic ───────────────────────────────────────────────
print(SEP)
print("STEP 6  — Post-deletion diagnostic (all orphan counts should be 0)")
print(SEP)

after_orphans = {}

for coll_name, fields in CHECKS:
    col = db[coll_name]
    total_docs   = col.count_documents({})
    orphan_count = 0

    for doc in col.find({}):
        found = False

        if coll_name == "conversations":
            raw = doc.get("participants", [])
            participants = raw if isinstance(raw, list) else [raw]
            ghost_parts = [p for p in participants if is_ghost(p)]
            valid_parts = [p for p in participants if not is_ghost(p)]
            if ghost_parts and not valid_parts:
                found = True
        else:
            for field, is_array in fields:
                raw = doc.get(field)
                if raw is None:
                    continue
                if is_array:
                    values = raw if isinstance(raw, list) else [raw]
                    if any(is_ghost(v) for v in values):
                        found = True
                        break
                else:
                    if is_ghost(raw):
                        found = True
                        break

        if found:
            orphan_count += 1

    after_orphans[coll_name] = {"total_remaining": total_docs, "orphans_remaining": orphan_count}

    mixed_note = f"  (+ {len(mixed_convs)} mixed intentionally kept)" if (coll_name == "conversations" and mixed_convs) else ""
    ok = "✓" if orphan_count == 0 else "⚠"
    print(f"\n  [{coll_name}]  {ok}  total_remaining={total_docs}  orphans_remaining={orphan_count}{mixed_note}")

print()


# ── 8. AFTER spot-check ───────────────────────────────────────────────────────
print(SEP)
print("STEP 7  — Spot-check: real user document counts (before vs after)")
print(SEP)

after_spot = {}
for uid in SPOT_USERS:
    after_spot[uid] = {
        "journal_entries":           db["journal_entries"].count_documents({"user_id": uid}),
        "messages_sent":             db["messages"].count_documents({"sender_id": uid}),
        "conversations":             db["conversations"].count_documents({"participants": uid}),
        "connection_requests_sent":  db["connection_requests"].count_documents({"sender_id": uid}),
        "connection_requests_recv":  db["connection_requests"].count_documents({"receiver_id": uid}),
    }

print()
all_intact = True
for uid in SPOT_USERS:
    b = before_spot[uid]
    a = after_spot[uid]
    mismatches = {k: (b[k], a[k]) for k in b if b[k] != a[k]}
    intact = not bool(mismatches)
    if not intact:
        all_intact = False
    tag = "✓ INTACT" if intact else "⚠ CHANGED"
    print(f"  user {uid}  [{tag}]")
    for k in b:
        flag = "  ← CHANGED!" if k in mismatches else ""
        print(f"    {k:<38} before={b[k]:<4}  after={a[k]}{flag}")
    print()

if all_intact:
    print("  ✓ All spot-checked real users are completely untouched.\n")
else:
    print("  ⚠ WARNING: Real user counts changed — investigate immediately!\n")


# ── 9. Master summary ─────────────────────────────────────────────────────────
summary = {
    "run_at_utc":          NOW_STR,
    "total_valid_users":   total_users,
    "mixed_conversations": {
        "count":            len(mixed_convs),
        "action":           "FLAGGED — NOT deleted",
        "backup_file":      str(mixed_backup_path),
        "ids":              [str(c["_id"]) for c in mixed_convs],
    },
    "backup_files":            backup_paths,
    "deletion_counts":         deletion_counts,
    "total_deleted":           sum(deletion_counts.values()),
    "post_deletion_orphans":   after_orphans,
    "spot_check": {
        "user_ids_checked": SPOT_USERS,
        "all_intact":       all_intact,
        "before":           before_spot,
        "after":            after_spot,
    },
}

summary_path = BACKUP_DIR / f"cleanup_summary_{NOW_STR}.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, default=bson_default)

print(SEP)
print("STEP 8  — Master summary")
print(SEP)
print(f"\n  Summary file → {summary_path}\n")

print(SEP)
print("  CLEANUP COMPLETE")
print(SEP)
print(f"  Valid users protected           : {total_users}")
print(f"  Mixed convs flagged (no delete) : {len(mixed_convs)}")
print(f"  Total documents deleted         : {sum(deletion_counts.values())}")
for coll, cnt in deletion_counts.items():
    print(f"    {coll:<30} {cnt} deleted")
print(f"  Real users untouched            : {'YES ✓' if all_intact else 'NO ⚠ CHECK ABOVE'}")
print(f"  Backup directory                : {BACKUP_DIR}")
print(f"  Summary JSON                    : {summary_path}")
print(SEP)
