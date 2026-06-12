"""
routes/history_routes.py — Prediction History Blueprint
--------------------------------------------------------
Manages a logged-in user's journal prediction history stored in MongoDB.

    GET    /history              — paginated history, newest first (JWT required)
    DELETE /history/<entry_id>  — delete a single entry (owner only, JWT required)
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

import db as _db

# ── Blueprint ──────────────────────────────────────────────────────────────
history_bp = Blueprint("history", __name__, url_prefix="/history")


# ── Helpers ────────────────────────────────────────────────────────────────

def _entry_to_dict(entry: dict) -> dict:
    """Return a JSON-serialisable representation of a journal_entries document."""
    created_at = entry.get("created_at")
    return {
        "id":         str(entry["_id"]),
        "journal":    entry.get("journal", ""),
        "risk":       entry.get("risk", ""),
        "confidence": entry.get("confidence"),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or ""),
    }


def _parse_positive_int(value: str | None, default: int, name: str):
    """
    Parse a query-string integer parameter.
    Returns (parsed_value, error_response | None).
    """
    if value is None:
        return default, None
    try:
        parsed = int(value)
        if parsed < 1:
            raise ValueError
        return parsed, None
    except (ValueError, TypeError):
        return None, (jsonify({"error": f"'{name}' must be a positive integer."}), 400)


# ── GET /history ───────────────────────────────────────────────────────────

@history_bp.route("", methods=["GET"])
@jwt_required()
def get_history():
    """
    Return the authenticated user's prediction history, newest first.

    Query parameters:
        page      (int, default 1)  — 1-indexed page number
        page_size (int, optional)   — override Config.HISTORY_PAGE_SIZE

    Success (200):
        {
            "entries":    [ { id, journal, risk, confidence, created_at }, ... ],
            "page":       1,
            "page_size":  10,
            "total":      42,
            "total_pages": 5,
            "has_next":   true,
            "has_prev":   false
        }

    Errors: 400 (bad params), 500 (database)
    """
    # get_jwt_identity() returns the user_id string (the 'sub' claim)
    user_id = get_jwt_identity()

    # ── Query-string params ────────────────────────────────────────
    default_page_size = current_app.config.get("HISTORY_PAGE_SIZE", 10)

    page, err = _parse_positive_int(request.args.get("page"), default=1, name="page")
    if err:
        return err

    page_size, err = _parse_positive_int(
        request.args.get("page_size"), default=default_page_size, name="page_size"
    )
    if err:
        return err

    # Cap page_size to prevent abuse (max 100 per request)
    page_size = min(page_size, 100)
    skip      = (page - 1) * page_size

    # ── MongoDB query ──────────────────────────────────────────────
    query_filter = {"user_id": user_id}

    try:
        total = _db.journal_entries_collection.count_documents(query_filter)

        cursor = (
            _db.journal_entries_collection
            .find(query_filter, {"__v": 0})          # exclude internal fields
            .sort("created_at", -1)                  # newest first
            .skip(skip)
            .limit(page_size)
        )
        entries = [_entry_to_dict(doc) for doc in cursor]

    except PyMongoError as e:
        current_app.logger.error(f"[HISTORY] DB error for user {user_id}: {e}")
        return jsonify({"error": "Database error. Please try again later."}), 500

    total_pages = max(1, -(-total // page_size))  # ceiling division

    return jsonify({
        "entries":     entries,
        "page":        page,
        "page_size":   page_size,
        "total":       total,
        "total_pages": total_pages,
        "has_next":    page < total_pages,
        "has_prev":    page > 1,
    }), 200


# ── DELETE /history/<entry_id> ─────────────────────────────────────────────

@history_bp.route("/<string:entry_id>", methods=["DELETE"])
@jwt_required()
def delete_entry(entry_id: str):
    """
    Delete a single prediction history entry.

    The authenticated user may only delete entries they own.

    Path parameter:
        entry_id  — MongoDB ObjectId string of the journal entry

    Success (200):
        { "message": "Entry deleted successfully." }

    Errors:
        400  — entry_id is not a valid ObjectId
        403  — entry belongs to a different user
        404  — entry not found
        500  — database error
    """
    # get_jwt_identity() returns the user_id string (the 'sub' claim)
    user_id = get_jwt_identity()

    # ── Validate ObjectId ──────────────────────────────────────────
    try:
        oid = ObjectId(entry_id)
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid entry ID format."}), 400

    # ── Fetch entry first to enforce ownership ─────────────────────
    try:
        entry = _db.journal_entries_collection.find_one({"_id": oid})
    except PyMongoError as e:
        current_app.logger.error(f"[HISTORY] DB fetch error for entry {entry_id}: {e}")
        return jsonify({"error": "Database error. Please try again later."}), 500

    if entry is None:
        return jsonify({"error": "Entry not found."}), 404

    # Ownership check — compare stored user_id to token identity
    if entry.get("user_id") != user_id:
        return jsonify({"error": "You do not have permission to delete this entry."}), 403

    # ── Delete ─────────────────────────────────────────────────────
    try:
        result = _db.journal_entries_collection.delete_one({"_id": oid})
    except PyMongoError as e:
        current_app.logger.error(f"[HISTORY] DB delete error for entry {entry_id}: {e}")
        return jsonify({"error": "Database error. Please try again later."}), 500

    if result.deleted_count == 0:
        # Rare race condition: entry was deleted between fetch and delete
        return jsonify({"error": "Entry not found."}), 404

    return jsonify({"message": "Entry deleted successfully."}), 200
