# -*- coding: utf-8 -*-
"""
check_db_direct.py
==================
Directly queries MongoDB to show all journal_entries
and diagnose why the predict route is not saving.
Also does a quick JWT decode to inspect the token claims.
"""

import os, sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from pymongo import MongoClient
import base64, json

# ── Connect directly to MongoDB ───────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI")
print(f"\n[DB] Connecting with URI: {MONGO_URI[:60]}...")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
client.admin.command("ping")
print("[DB] Connected OK\n")

db = client["mindease"]

# ── List all journal_entries ──────────────────────────────────────────────────
entries = list(db["journal_entries"].find({}).sort("created_at", -1).limit(10))
print(f"[DB] Total journal_entries in MongoDB: {db['journal_entries'].count_documents({})}")
print(f"[DB] Most recent 10:\n")

for i, e in enumerate(entries, 1):
    snippet = (e.get("journal") or "")[:60]
    print(f"  [{i}] _id={e['_id']}  user_id={e.get('user_id')}  risk={e.get('risk')}  snippet: {snippet!r}")

# ── Decode the last issued JWT to see its claims ──────────────────────────────
print("\n[JWT] Enter the JWT token from the last test run to inspect its claims.")
print("      (Or press Enter to skip)")
token = input("Token: ").strip()

if token:
    try:
        parts = token.split(".")
        # Add padding
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        print(f"\n[JWT] Decoded payload: {json.dumps(payload, indent=2)}")
        sub = payload.get("sub")
        print(f"\n[JWT] 'sub' (identity) = {sub!r}  (type={type(sub).__name__})")
    except Exception as e:
        print(f"[JWT] Failed to decode: {e}")

print("\n[DONE]\n")
