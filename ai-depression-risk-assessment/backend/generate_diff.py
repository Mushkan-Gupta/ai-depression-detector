import difflib

# Read current db.py
with open(r"f:\project\ai-depression-risk-assessment\backend\db.py", "r", encoding="utf-8") as f:
    current_db = f.readlines()

# Create original db.py
original_db = []
for line in current_db:
    if "conversations_collection" in line or "messages_collection" in line:
        if "global " in line:
            original_db.append(line.replace(", conversations_collection, messages_collection", ""))
        continue
    original_db.append(line)

with open(r"f:\project\ai-depression-risk-assessment\backend\routes\peer_routes.py", "r", encoding="utf-8") as f:
    current_peer = f.readlines()

original_peer = []
skip = False
for i, line in enumerate(current_peer):
    if "from utils.crisis_check import check_crisis_keywords" in line:
        continue
    if "# Auto-create conversation" in line:
        skip = True
        
    if skip and "except Exception as e:" in line:
        skip = False
        
    if "conversation_id" in line and "conv_id" in line and '"conversation_id": conv_id' in line:
        continue
        
    if "# ── GET /peer/conversations ────────────────────────────────────────────────" in line:
        break
        
    if not skip:
        original_peer.append(line)

with open("diff_output.txt", "w", encoding="utf-8") as out_f:
    out_f.write("--- db.py diff ---\n")
    for line in difflib.unified_diff(original_db, current_db, fromfile="a/backend/db.py", tofile="b/backend/db.py"):
        out_f.write(line)

    out_f.write("\n\n--- peer_routes.py diff ---\n")
    for line in difflib.unified_diff(original_peer, current_peer, fromfile="a/backend/routes/peer_routes.py", tofile="b/backend/routes/peer_routes.py"):
        out_f.write(line)


