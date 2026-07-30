"""
routes/peer_routes.py — Peer Connect Blueprint
-----------------------------------------------
Handles peer consent, peer matching, and connection requests:

    POST /peer/consent               — record consent to Peer Connect terms
    POST /peer/opt-in                — opt in to peer matching (jwt + consent required)
    POST /peer/opt-out               — opt out of peer matching (jwt + consent required)
    GET  /peer/candidates            — fetch anonymised top-5 match list (jwt + consent required)
    POST /peer/requests              — send a connection request (jwt + consent required)
    POST /peer/requests/<id>/accept  — accept a connection request (jwt + consent required)
    POST /peer/requests/<id>/decline — decline a connection request (jwt + consent required)
    GET  /peer/requests              — list incoming or sent requests (jwt + consent required)

Design notes
------------
• current_risk_level is written to users_collection by every /predict call
  (see app.py) — so matching always reads a fresh value, not a cached one.

• Crisis guidance content is mirrored verbatim from js/analyze.js
  GUIDANCE["High"] (lines 189-197).  The constant HIGH_RISK_CRISIS_GUIDANCE
  below is the single source of truth for the backend's High-risk 403 body;
  do not write new text here.

• The shared internal function _build_candidate_list() is called by both
  POST /peer/opt-in (on success) and GET /peer/candidates so the query and
  sort logic is defined exactly once.
"""

import random
from datetime import datetime, timedelta, timezone
from functools import wraps

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required

import db as _db
from utils.crisis_check import check_crisis_keywords

# ── Display-name generation ────────────────────────────────────────────────
# 50 calm/nature words — enough randomness to keep collision rate low
# (~1/50 for any two fresh users, negligible in small deployments).
_DISPLAY_NAME_WORDS = [
    "Aspen", "Birch", "Cedar", "Clover", "Coral",
    "Creek", "Dew", "Drift", "Dusk", "Fern",
    "Field", "Fjord", "Flint", "Fog", "Forest",
    "Glade", "Glen", "Grotto", "Grove", "Harbor",
    "Hazel", "Heather", "Inlet", "Iris", "Jasper",
    "Lake", "Lark", "Laurel", "Linden", "Lotus",
    "Maple", "Marsh", "Meadow", "Mesa", "Mist",
    "Moon", "Moss", "Opal", "Pebble", "Pine",
    "Pond", "Reef", "Ridge", "River", "Robin",
    "Sage", "Shore", "Stone", "Stream", "Vale",
]


def _generate_display_name() -> str:
    """Return 'Anonymous <Word>' using a randomly chosen word from the pool."""
    return f"Anonymous {random.choice(_DISPLAY_NAME_WORDS)}"

# ── Blueprint ──────────────────────────────────────────────────────────────
peer_bp = Blueprint("peer", __name__, url_prefix="/peer")

CONSENT_VERSION = "1.0"

# ── Crisis guidance ────────────────────────────────────────────────────────
# Source: js/analyze.js  GUIDANCE["High"]  (lines 189-197).
# Mirrored verbatim — do NOT edit this text independently of the frontend.
HIGH_RISK_CRISIS_GUIDANCE = {
    "summary": (
        "Your entry contains signals that suggest you may be experiencing a "
        "significant mental health crisis. Please know that you are not alone, "
        "and immediate support is available. Your life has immense value."
    ),
    "guidance": (
        "If you are having thoughts of ending your life or harming yourself, "
        "please reach out to a crisis line immediately — trained counselors are "
        "there 24/7 and want to help. You do not have to carry this alone. "
        "Talking to someone — a friend, family member, or professional — is a "
        "courageous and important step. Your feelings are real and valid, and "
        "with the right support, things can get better."
    ),
    "resources": [
        "🆘 iCall (India): 9152987821 (Mon–Sat, 8am–10pm)",
        "🆘 Vandrevala Foundation (India, 24/7): 1860-2662-345",
        "🆘 National Suicide Prevention Lifeline (US, 24/7): 988",
        "🆘 Samaritans (UK, 24/7): 116 123",
        "🆘 Crisis Text Line (Global): text HOME to 741741",
        "International Association for Suicide Prevention: iasp.info/resources/Crisis_Centres",
    ],
}


# ── Decorator ──────────────────────────────────────────────────────────────
def require_peer_consent(fn):
    """
    Decorator for Peer Connect routes to ensure the user has consented to the
    Peer Connect terms at the current CONSENT_VERSION.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        try:
            user = _db.users_collection.find_one({"_id": ObjectId(user_id)})
        except Exception as e:
            current_app.logger.error(f"[PEER_CONSENT] DB error: {e}")
            return jsonify({"error": "Database error"}), 500

        if not user:
            return jsonify({"error": "User not found"}), 404

        consent = user.get("peer_consent", {})
        if not consent.get("accepted") or consent.get("version") != CONSENT_VERSION:
            return jsonify({"error": "peer_consent_required"}), 403

        return fn(*args, **kwargs)
    return wrapper


# ── Internal: shared candidate query ──────────────────────────────────────

def _build_candidate_list(requester_id_str: str) -> list[dict]:
    """
    Fetch and return the top-5 anonymised candidate list for the given user.

    Query rules (all must hold):
      • available_for_matching == True
      • current_risk_level != "High"  (fresh read — written by /predict)
      • _id != requester
      • _id not in requester's excluded_users list
      • requester's _id not in candidate's excluded_users list  (bidirectional)
      • theme overlap with requester >= 1
      • no pending request between requester and candidate

    Sort: overlap descending, matching_started_at ascending (oldest waiter wins).
    Limit: 5.

    Returns a list of dicts with keys: candidate_id, peer_display_name,
    overlapping_themes.  Never returns risk level, email, or other PII.
    """
    try:
        requester_oid = ObjectId(requester_id_str)
        requester = _db.users_collection.find_one({"_id": requester_oid})
    except Exception as e:
        current_app.logger.error(f"[PEER_MATCH] DB error fetching requester: {e}")
        return []

    if not requester:
        return []

    requester_themes   = set(requester.get("themes", []))
    excluded_by_me     = [ObjectId(x) for x in requester.get("excluded_users", [])
                          if ObjectId.is_valid(x)]

    # ── Exclude users the requester already has a pending request with ──────
    # Covers both directions: requester sent, or requester received.
    try:
        pending_req_docs = list(_db.connection_requests_collection.find(
            {
                "status": "pending",
                "$or": [
                    {"sender_id":   requester_id_str},
                    {"receiver_id": requester_id_str},
                ],
            },
            {"sender_id": 1, "receiver_id": 1}
        ))
    except Exception as e:
        current_app.logger.error(f"[PEER_MATCH] DB error fetching pending requests: {e}")
        pending_req_docs = []

    already_requested_ids: set[str] = set()
    for pr in pending_req_docs:
        sid = pr.get("sender_id", "")
        rid = pr.get("receiver_id", "")
        # The other party (not the requester themselves)
        if sid == requester_id_str:
            already_requested_ids.add(rid)
        else:
            already_requested_ids.add(sid)

    # Base filter: opted-in, non-High, not self, not excluded by requester
    base_filter = {
        "available_for_matching": True,
        "current_risk_level":     {"$ne": "High"},
        "_id":                    {"$ne": requester_oid, "$nin": excluded_by_me},
    }

    try:
        raw_candidates = list(_db.users_collection.find(
            base_filter,
            {
                "_id":                  1,
                "peer_display_name":    1,
                "themes":               1,
                "matching_started_at":  1,
                "excluded_users":       1,
            }
        ))
    except Exception as e:
        current_app.logger.error(f"[PEER_MATCH] DB error fetching candidates: {e}")
        return []

    # Post-filter: bidirectional exclusion + theme overlap >= 1
    # + skip anyone the requester already has a pending request with
    scored = []
    requester_id_str_norm = str(requester_oid)

    for c in raw_candidates:
        cand_id_str = str(c["_id"])

        # Skip if there is already a pending request with this candidate
        if cand_id_str in already_requested_ids:
            continue

        # Bidirectional: skip if requester is in candidate's excluded list
        cand_excluded = [str(x) for x in c.get("excluded_users", [])]
        if requester_id_str_norm in cand_excluded:
            continue

        # Theme overlap
        cand_themes = set(c.get("themes", []))
        overlap = requester_themes & cand_themes
        if len(overlap) < 1:
            continue

        scored.append({
            "_id":                 c["_id"],
            "peer_display_name":   c.get("peer_display_name") or "Anonymous",
            "overlapping_themes":  sorted(overlap),
            "matching_started_at": c.get("matching_started_at"),
            "_overlap_count":      len(overlap),
        })

    # Sort: overlap desc, then matching_started_at asc (oldest waiter wins ties)
    # None timestamps go last
    scored.sort(
        key=lambda x: (
            -x["_overlap_count"],
            x["matching_started_at"] or datetime.max.replace(tzinfo=timezone.utc),
        )
    )

    top5 = scored[:5]

    return [
        {
            "candidate_id":       str(c["_id"]),
            "peer_display_name":  c["peer_display_name"],
            "overlapping_themes": c["overlapping_themes"],
        }
        for c in top5
    ]


# ── Routes ─────────────────────────────────────────────────────────────────

@peer_bp.route("/consent", methods=["POST"])
@jwt_required()
def consent_to_peer_connect():
    """
    Sets or updates the user's peer_consent object.
    Also auto-generates a peer_display_name the first time a user consents,
    if they do not already have one set.
    Returns the resulting peer_consent object.
    """
    user_id = get_jwt_identity()
    now = datetime.now(timezone.utc)

    new_consent = {
        "accepted":    True,
        "accepted_at": now,
        "version":     CONSENT_VERSION,
    }

    # ── Auto-generate peer_display_name if not already set ─────────────────
    try:
        existing_user = _db.users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"peer_display_name": 1}
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_CONSENT] DB fetch error: {e}")
        return jsonify({"error": "Database error"}), 500

    update_fields = {"peer_consent": new_consent}
    generated_name = None
    if not (existing_user or {}).get("peer_display_name"):
        generated_name = _generate_display_name()
        update_fields["peer_display_name"] = generated_name
        current_app.logger.info(
            f"[PEER_CONSENT] Auto-generated display name '{generated_name}' for user {user_id}"
        )

    try:
        _db.users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_CONSENT] DB update error: {e}")
        return jsonify({"error": "Failed to save consent"}), 500

    response_consent = {
        "accepted":    new_consent["accepted"],
        "accepted_at": new_consent["accepted_at"].isoformat(),
        "version":     new_consent["version"],
    }
    if generated_name:
        response_consent["peer_display_name"] = generated_name
    return jsonify(response_consent), 200


@peer_bp.route("/opt-in", methods=["POST"])
@jwt_required()
@require_peer_consent
def opt_in():
    """
    Opt the authenticated user in to peer matching.

    • Reads current_risk_level from users_collection (written by /predict).
    • If High: returns 403 with crisis guidance (no DB change).
    • Otherwise: sets available_for_matching = True and matching_started_at
      (only if not already set — idempotent on repeated calls).
    • On success: returns the current top-5 candidate list.
    """
    user_id = get_jwt_identity()

    try:
        user = _db.users_collection.find_one({"_id": ObjectId(user_id)})
    except Exception as e:
        current_app.logger.error(f"[PEER_OPT_IN] DB fetch error: {e}")
        return jsonify({"error": "Database error"}), 500

    if not user:
        return jsonify({"error": "User not found"}), 404

    # ── High-risk guard ────────────────────────────────────────────────────
    current_risk = user.get("current_risk_level", "")
    if current_risk == "High":
        return jsonify({
            "error":             "opt_in_unavailable_high_risk",
            "crisis_guidance":   HIGH_RISK_CRISIS_GUIDANCE,
        }), 403

    # ── Update DB (idempotent) ─────────────────────────────────────────────
    now = datetime.now(timezone.utc)

    # Set available_for_matching = True.
    # Set matching_started_at only if not already set (preserve original wait time).
    update_op = {"$set": {"available_for_matching": True}}
    if not user.get("matching_started_at"):
        update_op["$set"]["matching_started_at"] = now

    try:
        _db.users_collection.update_one({"_id": ObjectId(user_id)}, update_op)
    except Exception as e:
        current_app.logger.error(f"[PEER_OPT_IN] DB update error: {e}")
        return jsonify({"error": "Database error"}), 500

    # ── Return candidate list ──────────────────────────────────────────────
    candidates = _build_candidate_list(user_id)
    return jsonify({
        "message":    "Opted in to peer matching.",
        "candidates": candidates,
    }), 200


@peer_bp.route("/opt-out", methods=["POST"])
@jwt_required()
@require_peer_consent
def opt_out():
    """
    Opt the authenticated user out of peer matching.
    Clears available_for_matching and matching_started_at.
    """
    user_id = get_jwt_identity()

    try:
        _db.users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "available_for_matching": False,
                "matching_started_at":    None,
            }}
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_OPT_OUT] DB update error: {e}")
        return jsonify({"error": "Database error"}), 500

    return jsonify({"message": "Opted out of peer matching."}), 200


@peer_bp.route("/candidates", methods=["GET"])
@jwt_required()
@require_peer_consent
def get_candidates():
    """
    Return the top-5 anonymised peer match candidates for the authenticated user.

    The user must be opted in (available_for_matching == True).
    Returns an empty list if no candidates qualify — never an error.

    Response fields per candidate:
        candidate_id       — MongoDB _id string (needed later for connection requests)
        peer_display_name  — anonymised display name
        overlapping_themes — intersection of requester and candidate themes[]

    Never returns: risk level, email, wait time, full theme list, or any other PII.
    """
    user_id = get_jwt_identity()

    try:
        user = _db.users_collection.find_one(
            {"_id": ObjectId(user_id)},
            {"available_for_matching": 1, "current_risk_level": 1}
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_CANDIDATES] DB error: {e}")
        return jsonify({"error": "Database error"}), 500

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.get("current_risk_level") == "High":
        if user.get("available_for_matching"):
            try:
                _db.users_collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"available_for_matching": False, "matching_started_at": None}}
                )
            except Exception as e:
                current_app.logger.error(f"[PEER_CANDIDATES] DB update error: {e}")
        return jsonify({
            "error": "not_eligible_high_risk",
            "message": "Peer matching is not available right now. Crisis support resources are available.",
            "crisis_guidance": HIGH_RISK_CRISIS_GUIDANCE
        }), 403

    if not user.get("available_for_matching"):
        return jsonify({"error": "not_opted_in"}), 400

    candidates = _build_candidate_list(user_id)
    return jsonify({"candidates": candidates}), 200


# ═══════════════════════════════════════════════════════════════════════════
# Connection Requests
# ═══════════════════════════════════════════════════════════════════════════
#
# Document schema (connection_requests collection)
# -------------------------------------------------
# _id                    : ObjectId  — auto
# sender_id              : str       — JWT identity of the sender
# receiver_id            : str       — target user's _id string
# status                 : str       — "pending" | "accepted" | "declined" | "expired"
# created_at             : datetime
# expires_at             : datetime  — created_at + 72 h
# responded_at           : datetime | None  — set on accept/decline
# sender_risk_at_request : str       — sender's current_risk_level at send time
# receiver_risk_at_request: str      — receiver's current_risk_level at send time
# decline_reason         : str | None  — NEW additive field (non-breaking).
#   Set by the system when a request is auto-declined due to risk escalation
#   (value: "risk_escalation").  Also used on expiry-triggered auto-transitions
#   (value: "expired_on_access").  Null for manual accept/decline.
#
# Status transition rules
# -----------------------
# pending  → accepted  : receiver calls /accept within expiry window, both
#                        parties still non-High risk.
# pending  → declined  : receiver calls /decline, OR system auto-declines on
#                        risk escalation detected at accept time.
# pending  → expired   : lazy transition on any access after expires_at passes
#                        (before a risk-escalation auto-decline, expiry is
#                        checked first).
# Terminal states (accepted, declined, expired) are never re-opened.
# ═══════════════════════════════════════════════════════════════════════════

REQUEST_TTL_HOURS = 72


def _check_lazy_expiry(req: dict) -> dict | None:
    """
    If the request is still "pending" but expires_at has passed, transition
    it to "expired" in the DB and return the updated document.
    Returns None if no expiry transition was needed.
    """
    if req.get("status") != "pending":
        return None
    expires_at = req.get("expires_at")
    if expires_at and datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc
            if expires_at.tzinfo is None else expires_at.tzinfo):
        now = datetime.now(timezone.utc)
        try:
            updated = _db.connection_requests_collection.find_one_and_update(
                {"_id": req["_id"], "status": "pending"},
                {"$set": {
                    "status":         "expired",
                    "responded_at":   now,
                    "decline_reason": "expired_on_access",
                }},
                return_document=True,
            )
            return updated or req
        except Exception as e:
            current_app.logger.error(f"[PEER_REQ] Lazy expiry DB error: {e}")
    return None


def _serialize_request(req: dict, caller_id: str) -> dict:
    """
    Return only the fields safe to expose to either party.
    Never returns risk levels or any PII beyond what candidates already reveals.
    """
    out = {
        "id":          str(req["_id"]),
        "sender_id":   req.get("sender_id"),
        "receiver_id": req.get("receiver_id"),
        "status":      req.get("status"),
        "created_at":  req["created_at"].isoformat() if req.get("created_at") else None,
        "expires_at":  req["expires_at"].isoformat()  if req.get("expires_at")  else None,
        "responded_at": req["responded_at"].isoformat() if req.get("responded_at") else None,
    }
    if req.get("decline_reason"):
        out["decline_reason"] = req["decline_reason"]
    return out


# ── POST /peer/requests ────────────────────────────────────────────────────

@peer_bp.route("/requests", methods=["POST"])
@jwt_required()
@require_peer_consent
def send_request():
    """
    Send a connection request to another user.

    Body: { "receiver_id": "<ObjectId string>" }

    Eligibility is re-verified live using _build_candidate_list so that
    the same rules (opted-in, non-High risk, bidirectional exclusion,
    theme overlap >= 1) apply at request-send time, not just at matching time.
    """
    sender_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    receiver_id_str = (data.get("receiver_id") or "").strip()

    # ── Basic validation ───────────────────────────────────────────────────
    if not receiver_id_str:
        return jsonify({"error": "receiver_id is required"}), 400

    if receiver_id_str == sender_id:
        return jsonify({"error": "cannot send a request to yourself"}), 400

    if not ObjectId.is_valid(receiver_id_str):
        return jsonify({"error": "invalid receiver_id format"}), 400

    # ── Receiver must exist ────────────────────────────────────────────────
    try:
        receiver = _db.users_collection.find_one(
            {"_id": ObjectId(receiver_id_str)},
            {"_id": 1, "current_risk_level": 1},
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_REQ] DB error fetching receiver: {e}")
        return jsonify({"error": "Database error"}), 500

    if not receiver:
        return jsonify({"error": "receiver not found"}), 404

    # Eligibility re-verification
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
    sender_cand_ids     = {c["candidate_id"] for c in sender_candidates}
    if receiver_id_str not in sender_cand_ids:
        # Determine the most specific failure reason by direct inspection
        try:
            sender_doc   = _db.users_collection.find_one({"_id": ObjectId(sender_id)})
            receiver_doc = _db.users_collection.find_one({"_id": ObjectId(receiver_id_str)})
        except Exception:
            return jsonify({"error": "Database error"}), 500

        if not sender_doc or not sender_doc.get("available_for_matching"):
            reason = "you are not opted in to peer matching"
        elif not receiver_doc or not receiver_doc.get("available_for_matching"):
            reason = "receiver is not opted in to peer matching"
        elif (sender_doc.get("current_risk_level") == "High"
              or receiver_doc.get("current_risk_level") == "High"):
            reason = "one or both users currently have a high risk level"
        else:
            # Check exclusion before overlap
            sender_excluded   = [str(x) for x in sender_doc.get("excluded_users", [])]
            receiver_excluded = [str(x) for x in receiver_doc.get("excluded_users", [])]
            if (receiver_id_str in sender_excluded
                    or sender_id in receiver_excluded):
                reason = "one or both users have excluded the other"
            else:
                reason = "no theme overlap between users"

        return jsonify({"error": "not_eligible", "reason": reason}), 400

    # ── Check for existing pending request (either direction) ──────────────
    try:
        existing = _db.connection_requests_collection.find_one({
            "status": "pending",
            "$or": [
                {"sender_id": sender_id,    "receiver_id": receiver_id_str},
                {"sender_id": receiver_id_str, "receiver_id": sender_id},
            ],
        })
    except Exception as e:
        current_app.logger.error(f"[PEER_REQ] DB error checking duplicates: {e}")
        return jsonify({"error": "Database error"}), 500

    if existing:
        # Lazy expiry: if the found "pending" is actually expired, clear it
        expired = _check_lazy_expiry(existing)
        if not expired or expired.get("status") == "pending":
            # Still genuinely pending
            return jsonify({"error": "request already pending"}), 400
        # It was just transitioned to expired — fall through and allow new request

    # ── Capture risk snapshots and create document ─────────────────────────
    try:
        sender_doc_full = _db.users_collection.find_one(
            {"_id": ObjectId(sender_id)},
            {"current_risk_level": 1}
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_REQ] DB error fetching sender: {e}")
        return jsonify({"error": "Database error"}), 500

    now        = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=REQUEST_TTL_HOURS)

    new_req = {
        "sender_id":               sender_id,
        "receiver_id":             receiver_id_str,
        "status":                  "pending",
        "created_at":              now,
        "expires_at":              expires_at,
        "responded_at":            None,
        "sender_risk_at_request":  sender_doc_full.get("current_risk_level", "Unknown"),
        "receiver_risk_at_request": receiver.get("current_risk_level", "Unknown"),
        "decline_reason":          None,
    }

    try:
        result = _db.connection_requests_collection.insert_one(new_req)
        new_req["_id"] = result.inserted_id
    except Exception as e:
        current_app.logger.error(f"[PEER_REQ] DB insert error: {e}")
        return jsonify({"error": "Database error"}), 500

    return jsonify({"request": _serialize_request(new_req, sender_id)}), 201


# ── POST /peer/requests/<id>/accept ───────────────────────────────────────

@peer_bp.route("/requests/<string:request_id>/accept", methods=["POST"])
@jwt_required()
@require_peer_consent
def accept_request(request_id: str):
    """
    Accept a pending connection request.  Only the receiver may accept.

    Lazy checks in order:
      1. Expiry: if pending but past expires_at → transition to expired, 410.
      2. Risk escalation: if either party is now High → auto-decline, 409.
      3. Otherwise → accepted.
    """
    caller_id = get_jwt_identity()

    if not ObjectId.is_valid(request_id):
        return jsonify({"error": "invalid request id"}), 400

    try:
        req = _db.connection_requests_collection.find_one(
            {"_id": ObjectId(request_id)}
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_ACCEPT] DB error: {e}")
        return jsonify({"error": "Database error"}), 500

    if not req:
        return jsonify({"error": "request not found"}), 404

    # Only the receiver may accept
    if req.get("receiver_id") != caller_id:
        return jsonify({"error": "forbidden"}), 403

    # Terminal state guard
    if req.get("status") != "pending":
        return jsonify({"error": f"request is already {req.get('status')}"}), 409

    # 1. Lazy expiry check
    expired = _check_lazy_expiry(req)
    if expired and expired.get("status") == "expired":
        return jsonify({
            "error": "request_expired",
            "message": "This connection request expired before it could be accepted.",
        }), 410

    # 2. Lazy risk escalation check (fresh DB reads)
    try:
        sender_doc   = _db.users_collection.find_one(
            {"_id": ObjectId(req["sender_id"])},   {"current_risk_level": 1})
        receiver_doc = _db.users_collection.find_one(
            {"_id": ObjectId(req["receiver_id"])}, {"current_risk_level": 1})
    except Exception as e:
        current_app.logger.error(f"[PEER_ACCEPT] DB risk read error: {e}")
        return jsonify({"error": "Database error"}), 500

    sender_risk   = (sender_doc   or {}).get("current_risk_level", "")
    receiver_risk = (receiver_doc or {}).get("current_risk_level", "")

    if sender_risk == "High" or receiver_risk == "High":
        now = datetime.now(timezone.utc)
        try:
            _db.connection_requests_collection.update_one(
                {"_id": ObjectId(request_id), "status": "pending"},
                {"$set": {
                    "status":         "declined",
                    "responded_at":   now,
                    "decline_reason": "risk_escalation",
                }},
            )
        except Exception as e:
            current_app.logger.error(f"[PEER_ACCEPT] Risk-decline DB error: {e}")
        resp_data = {
            "error": "request_declined_risk_escalation",
            "message": (
                "This connection request could not be accepted because one or both "
                "users' risk level has changed since the request was sent. "
                "Crisis support resources are available."
            ),
        }
        if receiver_risk == "High":
            resp_data["crisis_guidance"] = HIGH_RISK_CRISIS_GUIDANCE
        return jsonify(resp_data), 409

    # 3. Accept
    now = datetime.now(timezone.utc)
    try:
        _db.connection_requests_collection.update_one(
            {"_id": ObjectId(request_id), "status": "pending"},
            {"$set": {"status": "accepted", "responded_at": now}},
        )
        
        # Auto-create conversation
        conv_doc = {
            "participants": [req["sender_id"], req["receiver_id"]],
            "connection_request_id": request_id,
            "status": "active",
            "closed_reason": None,
            "last_risk_check": now
        }
        res = _db.conversations_collection.insert_one(conv_doc)
        conv_id = str(res.inserted_id)
        
    except Exception as e:
        current_app.logger.error(f"[PEER_ACCEPT] DB accept error: {e}")
        return jsonify({"error": "Database error"}), 500

    return jsonify({
        "message":         "Connection request accepted.",
        "request_id":      request_id,
        "conversation_id": conv_id,
        "status":          "accepted",
        "responded_at":    now.isoformat(),
    }), 200


# ── POST /peer/requests/<id>/decline ──────────────────────────────────────

@peer_bp.route("/requests/<string:request_id>/decline", methods=["POST"])
@jwt_required()
@require_peer_consent
def decline_request(request_id: str):
    """
    Decline a pending connection request.  Only the receiver may decline.
    Lazy expiry is checked first.
    """
    caller_id = get_jwt_identity()

    if not ObjectId.is_valid(request_id):
        return jsonify({"error": "invalid request id"}), 400

    try:
        req = _db.connection_requests_collection.find_one(
            {"_id": ObjectId(request_id)}
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_DECLINE] DB error: {e}")
        return jsonify({"error": "Database error"}), 500

    if not req:
        return jsonify({"error": "request not found"}), 404

    if req.get("receiver_id") != caller_id:
        return jsonify({"error": "forbidden"}), 403

    if req.get("status") != "pending":
        return jsonify({"error": f"request is already {req.get('status')}"}), 409

    # Lazy expiry
    expired = _check_lazy_expiry(req)
    if expired and expired.get("status") == "expired":
        return jsonify({
            "error": "request_expired",
            "message": "This connection request already expired.",
        }), 410

    now = datetime.now(timezone.utc)
    try:
        _db.connection_requests_collection.update_one(
            {"_id": ObjectId(request_id), "status": "pending"},
            {"$set": {"status": "declined", "responded_at": now}},
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_DECLINE] DB update error: {e}")
        return jsonify({"error": "Database error"}), 500

    return jsonify({
        "message":      "Connection request declined.",
        "request_id":   request_id,
        "status":       "declined",
        "responded_at": now.isoformat(),
    }), 200


# ── GET /peer/requests ─────────────────────────────────────────────────────

@peer_bp.route("/requests", methods=["GET"])
@jwt_required()
@require_peer_consent
def list_requests():
    """
    List the caller's connection requests.

    Query param:
        type=incoming  — requests where caller is receiver
        type=sent      — requests where caller is sender

    Lazy expiry is applied to any pending requests in the result set.
    Response fields per request: id, sender_id, receiver_id, status,
    created_at, expires_at, responded_at, decline_reason (if set).
    Risk levels are never returned.
    """
    caller_id = get_jwt_identity()
    req_type  = request.args.get("type", "").strip().lower()

    if req_type not in ("incoming", "sent"):
        return jsonify({"error": "type must be 'incoming' or 'sent'"}), 400

    if req_type == "incoming":
        query = {"receiver_id": caller_id}
    else:
        query = {"sender_id": caller_id}

    try:
        docs = list(
            _db.connection_requests_collection.find(query)
            .sort("created_at", -1)
            .limit(100)
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_LIST] DB error: {e}")
        return jsonify({"error": "Database error"}), 500

    # Apply lazy expiry to any pending ones in-place
    result = []
    
    other_ids = [doc.get("sender_id") if req_type == "incoming" else doc.get("receiver_id") for doc in docs]
    try:
        other_users = list(_db.users_collection.find(
            {"_id": {"$in": [ObjectId(oid) for oid in other_ids if oid and ObjectId.is_valid(oid)]}}, 
            {"peer_display_name": 1}
        ))
        user_map = {str(u["_id"]): u.get("peer_display_name", "Anonymous") for u in other_users}
    except Exception as e:
        current_app.logger.error(f"[PEER_LIST] DB error fetching display names: {e}")
        user_map = {}

    for doc in docs:
        if doc.get("status") == "pending":
            updated = _check_lazy_expiry(doc)
            if updated:
                doc = updated
        serialized = _serialize_request(doc, caller_id)
        other_id = serialized.get("sender_id") if req_type == "incoming" else serialized.get("receiver_id")
        serialized["other_participant_name"] = user_map.get(other_id, "Anonymous")
        result.append(serialized)

    # Fetch caller's fresh risk level to check if they need crisis resources
    try:
        caller_doc = _db.users_collection.find_one(
            {"_id": ObjectId(caller_id)},
            {"current_risk_level": 1}
        )
    except Exception as e:
        current_app.logger.error(f"[PEER_LIST] DB error fetching caller risk: {e}")
        return jsonify({"error": "Database error"}), 500

    caller_risk = (caller_doc or {}).get("current_risk_level", "")

    resp_data = {"requests": result, "type": req_type}
    if caller_risk == "High":
        resp_data["crisis_guidance"] = HIGH_RISK_CRISIS_GUIDANCE

    return jsonify(resp_data), 200


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
    used_since_id = False
    if since_id:
        try:
            query["_id"] = {"$gt": ObjectId(since_id)}
            used_since_id = True
        except InvalidId:
            pass # ignore invalid since_id, just fetch all
            
    try:
        caller_doc = _db.users_collection.find_one({"_id": ObjectId(caller_id)}, {"current_risk_level": 1})
        cursor = _db.messages_collection.find(query).sort("_id", 1)
        if not used_since_id:
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

