import os

CODE = """

# ── GET /peer/conversations ────────────────────────────────────────────────

@peer_bp.route("/conversations", methods=["GET"])
@jwt_required()
@require_peer_consent
def list_conversations():
    caller_id = get_jwt_identity()
    try:
        convs = list(_db.conversations_collection.find({"participants": caller_id}).sort("_id", -1))
        
        # We need the other participant's display name
        other_ids = [c["participants"][0] if c["participants"][1] == caller_id else c["participants"][1] for c in convs]
        other_users = list(_db.users_collection.find({"_id": {"$in": [ObjectId(oid) for oid in other_ids]}}, {"peer_display_name": 1}))
        user_map = {str(u["_id"]): u.get("peer_display_name", "Anonymous") for u in other_users}

        result = []
        for c in convs:
            other_id = c["participants"][0] if c["participants"][1] == caller_id else c["participants"][1]
            result.append({
                "id": str(c["_id"]),
                "other_participant_name": user_map.get(other_id, "Anonymous"),
                "status": c.get("status", "active")
            })
        return jsonify({"conversations": result}), 200
    except Exception as e:
        current_app.logger.error(f"[PEER_CONV] DB error list: {e}")
        return jsonify({"error": "Database error"}), 500


# ── POST /peer/conversations/<id>/messages ─────────────────────────────────

@peer_bp.route("/conversations/<conv_id>/messages", methods=["POST"])
@jwt_required()
@require_peer_consent
def send_message(conv_id):
    caller_id = get_jwt_identity()
    data = request.get_json() or {}
    content = data.get("content", "").strip()
    
    if not content:
        return jsonify({"error": "content is required"}), 400
        
    try:
        conv = _db.conversations_collection.find_one({"_id": ObjectId(conv_id)})
    except InvalidId:
        return jsonify({"error": "Invalid conversation ID"}), 400
    except Exception as e:
        current_app.logger.error(f"[PEER_MSG] DB error fetch conv: {e}")
        return jsonify({"error": "Database error"}), 500
        
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    if caller_id not in conv.get("participants", []):
        return jsonify({"error": "forbidden"}), 403
        
    if conv.get("status") != "active":
        return jsonify({"error": "conversation is not active"}), 409
        
    other_id = conv["participants"][0] if conv["participants"][1] == caller_id else conv["participants"][1]

    # Risk escalation check
    try:
        caller_doc = _db.users_collection.find_one({"_id": ObjectId(caller_id)}, {"current_risk_level": 1})
        other_doc = _db.users_collection.find_one({"_id": ObjectId(other_id)}, {"current_risk_level": 1})
    except Exception as e:
        current_app.logger.error(f"[PEER_MSG] DB error fetch risk: {e}")
        return jsonify({"error": "Database error"}), 500
        
    caller_risk = (caller_doc or {}).get("current_risk_level", "")
    other_risk = (other_doc or {}).get("current_risk_level", "")
    
    if caller_risk == "High" or other_risk == "High":
        now = datetime.now(timezone.utc)
        try:
            _db.conversations_collection.update_one(
                {"_id": ObjectId(conv_id)},
                {"$set": {"status": "suspended", "closed_reason": "risk_escalation", "last_risk_check": now}}
            )
        except Exception as e:
            current_app.logger.error(f"[PEER_MSG] DB suspend error: {e}")
            
        resp_data = {
            "error": "conversation_suspended_risk_escalation",
            "message": "This conversation has been suspended because one or both users' risk level has changed. Crisis support resources are available."
        }
        if caller_risk == "High":
            resp_data["crisis_guidance"] = HIGH_RISK_CRISIS_GUIDANCE
        return jsonify(resp_data), 409

    # Keyword check
    is_flagged, kw_hits = check_crisis_keywords(content)
    now = datetime.now(timezone.utc)
    
    msg_doc = {
        "conversation_id": str(conv_id),
        "sender_id": caller_id,
        "content": content,
        "created_at": now,
        "crisis_flagged": is_flagged,
        "crisis_keywords_hit": kw_hits,
        "crisis_resources_shown": is_flagged
    }
    try:
        res = _db.messages_collection.insert_one(msg_doc)
        msg_doc["_id"] = str(res.inserted_id)
        msg_doc["created_at"] = msg_doc["created_at"].isoformat()
    except Exception as e:
        current_app.logger.error(f"[PEER_MSG] DB insert error: {e}")
        return jsonify({"error": "Database error"}), 500
        
    resp_data = {
        "message": "Message sent.",
        "msg": {k: v for k, v in msg_doc.items() if k not in ["crisis_flagged", "crisis_keywords_hit"]}
    }
    if is_flagged:
        resp_data["crisis_guidance"] = HIGH_RISK_CRISIS_GUIDANCE
        
    return jsonify(resp_data), 201


# ── GET /peer/conversations/<id>/messages ──────────────────────────────────

@peer_bp.route("/conversations/<conv_id>/messages", methods=["GET"])
@jwt_required()
@require_peer_consent
def list_messages(conv_id):
    caller_id = get_jwt_identity()
    since_id = request.args.get("since_id", "").strip()
    
    try:
        conv = _db.conversations_collection.find_one({"_id": ObjectId(conv_id)})
    except InvalidId:
        return jsonify({"error": "Invalid conversation ID"}), 400
    except Exception as e:
        current_app.logger.error(f"[PEER_MSG] DB error fetch conv: {e}")
        return jsonify({"error": "Database error"}), 500
        
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    if caller_id not in conv.get("participants", []):
        return jsonify({"error": "forbidden"}), 403

    query = {"conversation_id": str(conv_id)}
    if since_id:
        try:
            query["_id"] = {"$gt": ObjectId(since_id)}
        except InvalidId:
            pass # ignore invalid since_id, just fetch all
            
    try:
        caller_doc = _db.users_collection.find_one({"_id": ObjectId(caller_id)}, {"current_risk_level": 1})
        cursor = _db.messages_collection.find(query).sort("_id", 1)
        if not since_id:
            cursor = cursor.limit(200)
        docs = list(cursor)
    except Exception as e:
        current_app.logger.error(f"[PEER_MSG] DB fetch messages error: {e}")
        return jsonify({"error": "Database error"}), 500

    caller_risk = (caller_doc or {}).get("current_risk_level", "")

    result = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        if "created_at" in d and isinstance(d["created_at"], datetime):
            d["created_at"] = d["created_at"].isoformat()
        if d.get("sender_id") != caller_id:
            d.pop("crisis_flagged", None)
            d.pop("crisis_keywords_hit", None)
            d.pop("crisis_resources_shown", None)
        result.append(d)

    resp_data = {
        "messages": result,
        "conversation_status": conv.get("status", "unknown")
    }
    if caller_risk == "High":
        resp_data["crisis_guidance"] = HIGH_RISK_CRISIS_GUIDANCE

    return jsonify(resp_data), 200

"""

path = r"f:\project\ai-depression-risk-assessment\backend\routes\peer_routes.py"
with open(path, "a", encoding="utf-8") as f:
    f.write(CODE)

print("Appended routes successfully.")
