"""
verify_ist_timezone.py
Validates that Indian Standard Time (IST, UTC+5:30) is correctly applied
across auth, history, and peer routes.
"""

from datetime import datetime, timezone
from utils.tz_util import now_ist, to_ist_iso, to_ist, IST
from routes.history_routes import _entry_to_dict
from routes.auth_routes import _user_to_dict
from routes.peer_routes import _serialize_request
from bson import ObjectId

print("1. Testing now_ist()...")
cur = now_ist()
print(f"   now_ist(): {cur}")
assert "+05:30" in cur.isoformat(), f"Expected +05:30 offset in {cur.isoformat()}"
print("   Passed!")

print("\n2. Testing to_ist_iso() on naive UTC datetime (as stored in Mongo)...")
utc_naive = datetime(2026, 10, 9, 12, 0, 0) # 12:00 UTC -> 17:30 IST (+5:30)
ist_iso = to_ist_iso(utc_naive)
print(f"   UTC Naive: {utc_naive} -> IST ISO: {ist_iso}")
assert ist_iso == "2026-10-09T17:30:00+05:30", f"Unexpected converted time: {ist_iso}"
print("   Passed!")

print("\n3. Testing history_routes _entry_to_dict()...")
sample_entry = {
    "_id": ObjectId(),
    "journal": "Feeling hopeful today",
    "risk": "Low",
    "confidence": 0.85,
    "created_at": datetime(2026, 10, 9, 10, 0, 0) # 10:00 UTC -> 15:30 IST
}
dict_entry = _entry_to_dict(sample_entry)
print(f"   Converted entry created_at: {dict_entry['created_at']}")
assert dict_entry['created_at'] == "2026-10-09T15:30:00+05:30"
print("   Passed!")

print("\n4. Testing auth_routes _user_to_dict()...")
sample_user = {
    "_id": ObjectId(),
    "name": "Test User",
    "email": "test@example.com",
    "created_at": datetime(2026, 10, 9, 5, 0, 0) # 05:00 UTC -> 10:30 IST
}
dict_user = _user_to_dict(sample_user)
print(f"   Converted user created_at: {dict_user['created_at']}")
assert dict_user['created_at'] == "2026-10-09T10:30:00+05:30"
print("   Passed!")

print("\n5. Testing peer_routes _serialize_request()...")
sample_req = {
    "_id": ObjectId(),
    "sender_id": "user1",
    "receiver_id": "user2",
    "status": "pending",
    "created_at": datetime(2026, 10, 9, 4, 30, 0), # 04:30 UTC -> 10:00 IST
    "expires_at": datetime(2026, 10, 12, 4, 30, 0),
    "responded_at": None
}
dict_req = _serialize_request(sample_req, "user1")
print(f"   Converted req created_at: {dict_req['created_at']}")
print(f"   Converted req expires_at: {dict_req['expires_at']}")
assert dict_req['created_at'] == "2026-10-09T10:00:00+05:30"
assert dict_req['expires_at'] == "2026-10-12T10:00:00+05:30"
print("   Passed!")

print("\nALL IST TIMEZONE TESTS PASSED!")
