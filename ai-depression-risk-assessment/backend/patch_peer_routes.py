"""Patches peer_routes.py to add sender self-check before _build_candidate_list."""
import sys
path = r'F:\project\ai-depression-risk-assessment\backend\routes\peer_routes.py'
with open(path, encoding='utf-8') as f:
    src = f.read()

marker = 'Eligibility re-verification via candidate list'
idx = src.find(marker)
if idx == -1:
    sys.stdout.buffer.write(b'MARKER NOT FOUND\n'); sys.exit(1)

line_start = src.rfind('\n', 0, idx) + 1
end_marker = 'sender_cand_ids     = {c["candidate_id"] for c in sender_candidates}'
end_idx = src.find(end_marker, idx)
if end_idx == -1:
    sys.stdout.buffer.write(b'END MARKER NOT FOUND\n'); sys.exit(1)

block_end = end_idx + len(end_marker)
old_block = src[line_start:block_end]

new_block = '''    # Eligibility re-verification
    # IMPORTANT: _build_candidate_list filters High-risk users from appearing
    # AS CANDIDATES but does NOT check the caller/sender themselves.
    # Check the sender's own state explicitly first.
    try:
        sender_self = _db.users_collection.find_one(
            {"_id": ObjectId(sender_id)},
            {"current_risk_level": 1, "available_for_matching": 1}
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_REQ] DB error fetching sender self: {e}")
        return jsonify({"error": "Database error"}), 500

    if not sender_self or not sender_self.get("available_for_matching"):
        return jsonify({"error": "not_eligible",
                        "reason": "you are not opted in to peer matching"}), 400
    if sender_self.get("current_risk_level") == "High":
        return jsonify({"error": "not_eligible",
                        "reason": "one or both users currently have a high risk level"}), 400

    # Build the candidate list FROM THE SENDER'S PERSPECTIVE.
    # If the receiver appears there, the sender is eligible to send.
    sender_candidates   = _build_candidate_list(sender_id)
    sender_cand_ids     = {c["candidate_id"] for c in sender_candidates}'''

assert old_block in src, "patch anchor not found"
new_src = src.replace(old_block, new_block, 1)
assert new_src != src, "replacement was a no-op"
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_src)
sys.stdout.buffer.write(b'PATCHED OK\n')
