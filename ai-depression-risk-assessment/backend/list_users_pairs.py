import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=10000)
db = client["mindease"]

# Fetch all users
users = {str(u["_id"]): u for u in db["users"].find({})}
print("Total users:", len(users))
print()

# Fetch all conversations
convs = list(db["conversations"].find({}))
print("Total conversations:", len(convs))
print()

SEP = "-" * 70
print("=" * 70)
print("ALL USERS")
print("=" * 70)
for uid, u in users.items():
    print("  ID    :", uid)
    print("  Name  :", u.get("name", "(no name)"))
    print("  Email :", u.get("email", "(no email)"))
    print()

print("=" * 70)
print("ALL CONVERSATION PAIRS")
print("=" * 70)
for i, conv in enumerate(convs, 1):
    parts = conv.get("participants", [])
    names = []
    for p in parts:
        u = users.get(str(p))
        if u:
            names.append("%s (%s)" % (u.get("name","?"), str(p)[:8]+"..."))
        else:
            names.append("GHOST (%s...)" % str(p)[:8])
    print("  [%d] conv_id: %s" % (i, conv["_id"]))
    for n in names:
        print("       -> %s" % n)
    print()
