import json, os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=10000)
db = client["mindease"]
valid_ids = set(str(u["_id"]) for u in db["users"].find({}, {"_id": 1}))

backup_dir = Path(__file__).parent / "orphan_backups"

print("=== RETROSPECTIVE ANALYSIS ===\n")

cr_file = sorted(backup_dir.glob("connection_requests_orphans_*.json"))[-1]
with open(cr_file, encoding="utf-8") as f:
    cr_docs = json.load(f)

sv_rg, sg_rv, bg = [], [], []
for doc in cr_docs:
    s = str(doc.get("sender_id",""))
    r = str(doc.get("receiver_id",""))
    if (s in valid_ids) and (r not in valid_ids):
        sv_rg.append(doc)
    elif (s not in valid_ids) and (r in valid_ids):
        sg_rv.append(doc)
    else:
        bg.append(doc)

print("connection_requests deleted:", len(cr_docs))
print("  both_ghost:", len(bg))
print("  sender=VALID receiver=ghost:", len(sv_rg))
print("  sender=ghost receiver=VALID:", len(sg_rv))

pr_file = sorted(backup_dir.glob("peer_reports_orphans_*.json"))[-1]
with open(pr_file, encoding="utf-8") as f:
    pr_docs = json.load(f)
print("\npeer_reports deleted:", len(pr_docs))
for doc in pr_docs:
    rep = str(doc.get("reporter_id",""))
    rpd = str(doc.get("reported_user_id",""))
    print("  reporter_valid=%s reported_valid=%s" % (rep in valid_ids, rpd in valid_ids))

msg_file = sorted(backup_dir.glob("messages_orphans_*.json"))[-1]
with open(msg_file, encoding="utf-8") as f:
    msg_docs = json.load(f)
valid_senders = [d for d in msg_docs if str(d.get("sender_id","")) in valid_ids]
print("\nmessages deleted:", len(msg_docs))
print("  sender=VALID (unexpected):", len(valid_senders))

je_file = sorted(backup_dir.glob("journal_entries_orphans_*.json"))[-1]
with open(je_file, encoding="utf-8") as f:
    je_docs = json.load(f)
valid_owner = [d for d in je_docs if str(d.get("user_id","")) in valid_ids]
print("\njournal_entries deleted:", len(je_docs))
print("  user_id=VALID (unexpected):", len(valid_owner))

conv_file = sorted(backup_dir.glob("conversations_orphans_*.json"))[-1]
with open(conv_file, encoding="utf-8") as f:
    conv_docs = json.load(f)
has_valid = [d for d in conv_docs if any(str(p) in valid_ids for p in d.get("participants",[]))]
print("\nconversations deleted:", len(conv_docs))
print("  has_valid_participant (unexpected):", len(has_valid))
