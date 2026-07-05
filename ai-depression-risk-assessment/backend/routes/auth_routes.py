"""
routes/auth_routes.py — Authentication Blueprint
-------------------------------------------------
Handles all user account operations:

    POST  /auth/register  — create a new account, return JWT
    POST  /auth/login     — verify credentials, return JWT
    GET   /auth/me        — return current user profile (JWT required)
    POST  /auth/logout    — server-side logout acknowledgement (JWT required)
    PUT   /auth/profile   — update display name (JWT required)
    POST  /auth/google    — Google Sign-In (GIS ID-token), return JWT
"""

from datetime import datetime, timezone

from bson import ObjectId
from email_validator import validate_email, EmailNotValidError
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from werkzeug.security import check_password_hash, generate_password_hash

import db as _db

# ── Blueprint ──────────────────────────────────────────────────────────────
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ── Helpers ────────────────────────────────────────────────────────────────

def _user_to_dict(user: dict) -> dict:
    """Return a safe, serialisable representation of a user document."""
    return {
        "id":            str(user["_id"]),
        "name":          user.get("name", ""),
        "email":         user.get("email", ""),
        "picture":       user.get("picture", ""),
        "auth_provider": user.get("auth_provider", "email"),
        "created_at":    user.get("created_at", "").isoformat()
                         if isinstance(user.get("created_at"), datetime)
                         else str(user.get("created_at", "")),
    }


def _validate_email_address(email: str) -> str:
    """
    Normalise and validate an email address using email-validator.
    Returns the normalised email string on success.
    Raises ValueError with a user-friendly message on failure.
    """
    try:
        info = validate_email(email, check_deliverability=False)
        return info.normalized
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc


def _validate_password(password: str) -> None:
    """
    Enforce a minimum password policy:
      - At least 8 characters
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
    Raises ValueError with a descriptive message on failure.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit.")


# ── POST /auth/register ────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user account.

    Request body (JSON):
        {
            "name":     "Jane Doe",      -- required
            "email":    "jane@example.com",  -- required, must be unique
            "password": "Secret123"      -- required, min policy enforced
        }

    Success (201):
        {
            "message":      "Account created successfully.",
            "access_token": "<jwt>",
            "user":         { id, name, email, created_at }
        }

    Errors: 400 (validation), 409 (email taken), 500 (server)
    """
    data = request.get_json(silent=True)

    # ── Input presence check ───────────────────────────────────
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    name     = (data.get("name", "") or "").strip()
    email    = (data.get("email", "") or "").strip()
    password = (data.get("password", "") or "").strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400
    if len(name) > 100:
        return jsonify({"error": "Name must be 100 characters or fewer."}), 400

    # ── Email validation ───────────────────────────────────────
    try:
        email = _validate_email_address(email)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # ── Password validation ────────────────────────────────────
    try:
        _validate_password(password)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # ── Duplicate email check ──────────────────────────────────
    try:
        existing = _db.users_collection.find_one({"email": email})
    except Exception:
        return jsonify({"error": "Database error. Please try again later."}), 500

    if existing:
        return jsonify({"error": "An account with this email already exists."}), 409

    # ── Persist new user ───────────────────────────────────────
    password_hash = generate_password_hash(password)
    new_user = {
        "name":          name,
        "email":         email,
        "password_hash": password_hash,
        "created_at":    datetime.now(timezone.utc),
    }

    try:
        result       = _db.users_collection.insert_one(new_user)
        new_user["_id"] = result.inserted_id
    except Exception:
        return jsonify({"error": "Failed to create account. Please try again."}), 500

    # ── Issue JWT ──────────────────────────────────────────────
    # Identity is the user_id string (sub claim).
    # Extra info is stored as additional claims.
    access_token = create_access_token(
        identity=str(result.inserted_id),
        additional_claims={
            "email": email,
            "name":  name,
        }
    )

    return jsonify({
        "message":      "Account created successfully.",
        "access_token": access_token,
        "user":         _user_to_dict(new_user),
    }), 201


# ── POST /auth/login ───────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate an existing user.

    Request body (JSON):
        {
            "email":    "jane@example.com",
            "password": "Secret123"
        }

    Success (200):
        {
            "message":      "Login successful.",
            "access_token": "<jwt>",
            "user":         { id, name, email, created_at }
        }

    Errors: 400 (missing fields), 401 (invalid credentials), 500 (server)
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    email    = (data.get("email", "") or "").strip()
    password = (data.get("password", "") or "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    # ── Look up user ───────────────────────────────────────────
    try:
        user = _db.users_collection.find_one({"email": email})
    except Exception:
        return jsonify({"error": "Database error. Please try again later."}), 500

    # Intentionally vague message — don't reveal whether the email exists.
    if not user or not check_password_hash(user.get("password_hash", ""), password):
        return jsonify({"error": "Invalid email or password."}), 401

    # ── Issue JWT ──────────────────────────────────────────────
    access_token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={
            "email": user["email"],
            "name":  user.get("name", ""),
        }
    )

    return jsonify({
        "message":      "Login successful.",
        "access_token": access_token,
        "user":         _user_to_dict(user),
    }), 200


# ── GET /auth/me ───────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    Return the currently authenticated user's profile.
    Requires a valid Bearer token in the Authorization header.

    Success (200):
        {
            "user": { id, name, email, created_at }
        }

    Errors: 401 (missing/invalid token), 404 (user deleted), 500 (server)
    """
    # get_jwt_identity() now returns the user_id string (the 'sub' claim)
    user_id = get_jwt_identity()

    try:
        user = _db.users_collection.find_one(
            {"_id": ObjectId(user_id)}
        )
    except Exception:
        return jsonify({"error": "Database error. Please try again later."}), 500

    if not user:
        return jsonify({"error": "User account not found."}), 404

    return jsonify({"user": _user_to_dict(user)}), 200


# ── POST /auth/logout ──────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Stateless JWT logout.

    Because JWTs are self-contained and we do not maintain a token blocklist,
    logout is implemented on the client side (the frontend clears its stored token).
    This endpoint exists so that:
      1. Clients have a standard endpoint to call for a clean logout flow.
      2. Server-side logout logic (e.g. blocklist) can be added here in the future
         without changing any frontend code.

    Success (200):
        { "message": "Logged out successfully." }

    Errors: 401 (missing/invalid token)
    """
    return jsonify({"message": "Logged out successfully."}), 200


# ── PUT /auth/profile ──────────────────────────────────────────────────────

@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """
    Update the authenticated user's display name.

    Request body (JSON):
        {
            "name": "New Name"   -- required, 1–100 characters
        }

    Success (200):
        {
            "message": "Profile updated successfully.",
            "user":    { id, name, email, created_at }
        }

    Errors: 400 (validation), 404 (user deleted), 500 (server)
    """
    user_id = get_jwt_identity()

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    name = (data.get("name", "") or "").strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400
    if len(name) > 100:
        return jsonify({"error": "Name must be 100 characters or fewer."}), 400

    try:
        result = _db.users_collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": {"name": name}},
            return_document=True,
        )
    except Exception:
        return jsonify({"error": "Database error. Please try again later."}), 500

    if not result:
        return jsonify({"error": "User account not found."}), 404

    return jsonify({
        "message": "Profile updated successfully.",
        "user":    _user_to_dict(result),
    }), 200


# ── POST /auth/google ──────────────────────────────────────────────────────

@auth_bp.route("/google", methods=["POST"])
def google_signin():
    """
    Google Sign-In via Google Identity Services (GIS).

    The frontend sends the ID token returned by the GIS popup directly to
    this endpoint. The backend verifies it server-side using google-auth,
    then upserts the user and issues the same JWT used by email/password
    login — so all existing protected routes work unchanged.

    Request body (JSON):
        { "credential": "<google_id_token>" }

    Success (200):
        {
            "message":      "Google sign-in successful.",
            "access_token": "<jwt>",
            "user":         { id, name, email, picture, auth_provider, created_at }
        }

    Errors: 400 (missing token), 401 (invalid/expired token), 500 (server)
    """
    data = request.get_json(silent=True)
    if not data or not data.get("credential"):
        return jsonify({"error": "Google credential token is required."}), 400

    credential = data["credential"]
    google_client_id = current_app.config.get("GOOGLE_CLIENT_ID")

    # ── Server-side verification ───────────────────────────────
    # verify_oauth2_token checks: signature, audience, issuer, expiration.
    # Never skip this — never trust client-side Google auth data directly.
    try:
        id_info = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            google_client_id,
        )
    except ValueError as exc:
        # Covers: wrong audience, expired token, bad signature, malformed token
        return jsonify({"error": f"Invalid Google token: {exc}"}), 401
    except Exception:
        return jsonify({"error": "Token verification failed. Please try again."}), 401

    # ── Extract verified claims ────────────────────────────────
    google_sub = id_info.get("sub")          # stable unique Google user ID
    email      = id_info.get("email", "").lower().strip()
    name       = id_info.get("name", "").strip()
    picture    = id_info.get("picture", "")  # profile photo URL (may be empty)

    if not email or not google_sub:
        return jsonify({"error": "Google account did not provide an email address."}), 401

    # ── Upsert user ────────────────────────────────────────────
    # Strategy:
    #   1. Look up by email (handles both new Google users and existing
    #      email/password users linking their Google account).
    #   2. If found: merge Google fields without touching password_hash.
    #   3. If not found: create a new account (no password_hash — Google only).
    try:
        existing = _db.users_collection.find_one({"email": email})
    except Exception:
        return jsonify({"error": "Database error. Please try again later."}), 500

    now = datetime.now(timezone.utc)

    if existing:
        # Merge Google identity onto the existing account.
        # Only update fields that come from Google; never overwrite password_hash.
        update_fields = {
            "google_sub":     google_sub,
            "picture":        picture,
            "auth_provider":  "google" if not existing.get("password_hash") else "both",
        }
        # Only update name if the user has not customised it (i.e. it's still the
        # Google name or is blank — preserves manual name changes from /auth/profile).
        if not existing.get("name") or existing.get("google_sub") == google_sub:
            update_fields["name"] = name or existing.get("name", "")

        try:
            user = _db.users_collection.find_one_and_update(
                {"_id": existing["_id"]},
                {"$set": update_fields},
                return_document=True,
            )
        except Exception:
            return jsonify({"error": "Database error. Please try again later."}), 500
    else:
        # First-time Google sign-in — create a new account.
        # No password_hash stored; auth_provider="google".
        new_user = {
            "name":          name,
            "email":         email,
            "google_sub":    google_sub,
            "picture":       picture,
            "auth_provider": "google",
            "created_at":    now,
            # password_hash intentionally omitted — Google-only account
        }
        try:
            result   = _db.users_collection.insert_one(new_user)
            new_user["_id"] = result.inserted_id
            user     = new_user
        except Exception:
            return jsonify({"error": "Failed to create account. Please try again."}), 500

    # ── Issue JWT (same format as email/password login) ────────
    access_token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={
            "email": email,
            "name":  user.get("name", ""),
        }
    )

    return jsonify({
        "message":      "Google sign-in successful.",
        "access_token": access_token,
        "user":         _user_to_dict(user),
    }), 200
