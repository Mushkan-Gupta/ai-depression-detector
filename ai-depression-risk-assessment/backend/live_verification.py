"""
Live verification script â€” scenarios (c) and (d).
Hits the live Flask server at http://127.0.0.1:5000 and queries MongoDB directly.
"""
import sys, json, time, random, string, requests
from pymongo import MongoClient
from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime, timezone, timedelta
import os

BASE = "http://127.0.0.1:5000"

# ---------- helpers ----------

def rand_suffix(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

def sep(label):
    print("\n" + "="*60)
    print(f"  {label}")
    print("="*60)

def show_req(method, url, payload=None):
    print(f"\n>>> {method} {url}")
    if payload:
        print(f"    body: {json.dumps(payload)}")

def show_resp(r, label=""):
    prefix = f"[{label}] " if label else ""
    print(f"\n{prefix}HTTP {r.status_code} {r.reason}")
    try:
        body = r.json()
        print(json.dumps(body, indent=2, default=str))
    except Exception:
        print(r.text[:2000])
    return r

def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def register_and_login(email, name="Verify TestUser", password="TestPass123!"):
    """Register a brand-new user, return JWT token."""
    show_req("POST", f"{BASE}/auth/register", {"name": name, "email": email, "password": "..."})
    r = requests.post(f"{BASE}/auth/register",
                      json={"name": name, "email": email, "password": password},
                      timeout=10)
    show_resp(r, "REGISTER")
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Register failed: {r.status_code} {r.text}")

    show_req("POST", f"{BASE}/auth/login", {"email": email, "password": "..."})
    r = requests.post(f"{BASE}/auth/login",
                      json={"email": email, "password": password},
                      timeout=10)
    show_resp(r, "LOGIN")
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        raise RuntimeError(f"No token in login response: {data}")
    return token

# ---------- MongoDB ----------
env_path = os.path.join(os.path.dirname(__file__), ".env")
mongo_uri = None
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("MONGO_URI", "MONGODB_URI"):
                mongo_uri = v.strip().strip('"').strip("'")
                break
if not mongo_uri:
    raise RuntimeError("MONGO_URI not found in .env")

print(f"Connecting to MongoDB...")
mc = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
db = mc["mindease"]   # from db.py line 99
users_col: Collection = db["users"]
conn_req_col: Collection = db["connection_requests"]
print(f"MongoDB: connected. DB=mindease, users={users_col.count_documents({})}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  SCENARIO (c)
#  Fresh user (never existed before) â†’ POST /peer/consent â†’ read MongoDB doc
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
sep("SCENARIO (c)")
suffix_c = rand_suffix()
email_c  = f"verify.c.{suffix_c}@example.com"
print(f"\nFresh user email: {email_c}")
print("(Confirming not already in DB...)")
assert users_col.find_one({"email": email_c}) is None, "Email collision â€” retry"
print("  â†’ not in DB. Good.\n")

token_c = register_and_login(email_c)

sep("(c) Calling POST /peer/consent  {consent: true}")
r_consent = requests.post(
    f"{BASE}/peer/consent",
    json={"consent": True},
    headers=auth_headers(token_c),
    timeout=10,
)

print("\nâ”€â”€â”€ RAW HTTP RESPONSE â”€â”€â”€")
print(f"Status : {r_consent.status_code} {r_consent.reason}")
print(f"Headers: {dict(r_consent.headers)}")
print("\nBody:")
try:
    consent_body = r_consent.json()
    print(json.dumps(consent_body, indent=2, default=str))
except Exception:
    print(r_consent.text)

sep("(c) Direct MongoDB read â€” users collection")
user_doc = users_col.find_one({"email": email_c})
if user_doc is None:
    print("ERROR: user document not found in MongoDB!")
    sys.exit(1)

doc_out = {}
for k, v in user_doc.items():
    if k in ("password", "password_hash"):
        doc_out[k] = "<REDACTED>"
    else:
        doc_out[k] = v

print("\nRAW MongoDB document (passwords redacted):")
print(json.dumps(doc_out, indent=2, default=str))

print(f"\n  peer_display_name : {user_doc.get('peer_display_name', '*** FIELD MISSING ***')}")
print(f"  peer_consent      : {user_doc.get('peer_consent', '*** FIELD MISSING ***')}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  SCENARIO (d)
#  Two real users â†’ POST /peer/requests via actual API flow â†’
#  GET /peer/candidates confirms receiver absent from sender's list
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
sep("SCENARIO (d)")
suffix_d1 = rand_suffix()
suffix_d2 = rand_suffix()
email_d1  = f"verify.d1.{suffix_d1}@example.com"
email_d2  = f"verify.d2.{suffix_d2}@example.com"
print(f"\nSender   email: {email_d1}")
print(f"Receiver email: {email_d2}")
assert users_col.find_one({"email": email_d1}) is None
assert users_col.find_one({"email": email_d2}) is None
print("Both not in DB. Good.")

token_d1 = register_and_login(email_d1, name="Sender User")
token_d2 = register_and_login(email_d2, name="Receiver User")

sep("(d) Both users POST /peer/consent")
r = requests.post(f"{BASE}/peer/consent", json={"consent": True}, headers=auth_headers(token_d1), timeout=10)
show_resp(r, "SENDER CONSENT")

r = requests.post(f"{BASE}/peer/consent", json={"consent": True}, headers=auth_headers(token_d2), timeout=10)
show_resp(r, "RECEIVER CONSENT")

# Both users need: available_for_matching=True, themes with overlap, current_risk_level != High
# We set this directly in MongoDB (simulating what /predict + /peer/opt-in would do)
# This is the most faithful test because POST /peer/requests reads these fields live
sender_doc   = users_col.find_one({"email": email_d1})
receiver_doc = users_col.find_one({"email": email_d2})
sender_id    = str(sender_doc["_id"])
receiver_id  = str(receiver_doc["_id"])

sep("(d) Setting up both users as opted-in via POST /peer/opt-in")
# First inject themes + risk level directly (necessary because /predict isn't being tested here)
shared_themes = ["anxiety", "low_mood"]
now = datetime.now(timezone.utc)
users_col.update_one(
    {"_id": sender_doc["_id"]},
    {"$set": {
        "themes":             shared_themes,
        "current_risk_level": "Low",
        "available_for_matching": False,   # will be set True by /peer/opt-in
        "matching_started_at": None,
    }}
)
users_col.update_one(
    {"_id": receiver_doc["_id"]},
    {"$set": {
        "themes":             shared_themes,
        "current_risk_level": "Low",
        "available_for_matching": False,
        "matching_started_at": None,
    }}
)
print(f"  MongoDB: themes={shared_themes}, risk=Low set for both users")

# Now call POST /peer/opt-in for both users (actual API)
show_req("POST", f"{BASE}/peer/opt-in")
r = requests.post(f"{BASE}/peer/opt-in", headers=auth_headers(token_d1), timeout=10)
show_resp(r, "SENDER OPT-IN")
if r.status_code != 200:
    raise RuntimeError(f"Sender opt-in failed: {r.status_code} {r.text}")

r = requests.post(f"{BASE}/peer/opt-in", headers=auth_headers(token_d2), timeout=10)
show_resp(r, "RECEIVER OPT-IN")
if r.status_code != 200:
    raise RuntimeError(f"Receiver opt-in failed: {r.status_code} {r.text}")

sep("(d) Sender calls POST /peer/requests to Receiver")
show_req("POST", f"{BASE}/peer/requests", {"receiver_id": receiver_id})
r_req = requests.post(
    f"{BASE}/peer/requests",
    json={"receiver_id": receiver_id},
    headers=auth_headers(token_d1),
    timeout=10,
)
print(f"\nâ”€â”€â”€ RAW HTTP RESPONSE for POST /peer/requests â”€â”€â”€")
print(f"Status : {r_req.status_code} {r_req.reason}")
print("\nBody:")
try:
    req_body = r_req.json()
    print(json.dumps(req_body, indent=2, default=str))
except Exception:
    print(r_req.text)

if r_req.status_code not in (200, 201):
    raise RuntimeError(f"Send request failed: {r_req.status_code} {r_req.text}")

sep("(d) Direct MongoDB read â€” connection_requests document")
req_doc = conn_req_col.find_one({
    "sender_id":   sender_id,
    "receiver_id": receiver_id,
})
if req_doc is None:
    # IDs might be stored as ObjectId
    req_doc = conn_req_col.find_one({
        "sender_id":   ObjectId(sender_id),
        "receiver_id": ObjectId(receiver_id),
    })
if req_doc is None:
    print("  (trying any combination...)")
    for d in conn_req_col.find().sort("created_at", -1).limit(5):
        print(json.dumps(d, indent=2, default=str))
else:
    print("\nRAW connection_requests document:")
    print(json.dumps(req_doc, indent=2, default=str))

sep("(d) Sender calls GET /peer/candidates â€” receiver must be absent")
show_req("GET", f"{BASE}/peer/candidates")
r_cands = requests.get(
    f"{BASE}/peer/candidates",
    headers=auth_headers(token_d1),
    timeout=10,
)
print(f"\nâ”€â”€â”€ RAW HTTP RESPONSE for GET /peer/candidates â”€â”€â”€")
print(f"Status : {r_cands.status_code} {r_cands.reason}")
print("\nBody (full raw JSON):")
try:
    cands_json = r_cands.json()
    print(json.dumps(cands_json, indent=2, default=str))
    # Check receiver_id presence
    candidates = cands_json.get("candidates", cands_json) if isinstance(cands_json, dict) else cands_json
    ids_in_list = [str(c.get("candidate_id","")) for c in candidates]
    print(f"\n  candidate_ids in response : {ids_in_list}")
    print(f"  receiver_id               : {receiver_id}")
    if receiver_id in ids_in_list:
        print("  âœ— FAIL â€” receiver is present in the candidates list! Filtering is broken.")
    else:
        print("  âœ“ PASS â€” receiver is NOT in the candidates list. Pending-request exclusion works.")
except Exception as ex:
    print(r_cands.text)
    print(f"  (parse error: {ex})")

print("\n" + "="*60)
print("  ALL VERIFICATION COMPLETE")
print("="*60)

