"""
db.py — MongoDB Atlas Connection & Collection Handles
-----------------------------------------------------
Initialises a single MongoClient for the application lifetime and
exposes typed collection accessors used by routes and services.

Usage in app.py:
    from db import init_db
    init_db(app)

Usage in routes (IMPORTANT — always import the module, never the collections
directly, because direct imports capture None before init_db() has run):
    import db as _db
    _db.users_collection.find_one(...)
    _db.journal_entries_collection.insert_one(...)
"""

import sys
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ConfigurationError, ServerSelectionTimeoutError

# Module-level references — populated once by init_db()
_client:   MongoClient | None = None
_db                           = None

users_collection:            Collection | None = None
journal_entries_collection:  Collection | None = None


# ── Initialiser ────────────────────────────────────────────────────────────

def init_db(app) -> None:
    """
    Connect to MongoDB Atlas and bind collection handles.

    Called once from app.py after the Flask app is created:
        from db import init_db
        init_db(app)

    On success, sets the module-level collection handles.
    On failure, logs the error and exits — the server should not
    start without a valid database connection.
    """
    global _client, _db, users_collection, journal_entries_collection

    mongo_uri = app.config.get("MONGO_URI")
    if not mongo_uri:
        print("[DB] FATAL: MONGO_URI is not set in app config.", file=sys.stderr)
        sys.exit(1)

    try:
        # serverSelectionTimeoutMS prevents the app from hanging indefinitely
        # when Atlas is unreachable (e.g. wrong URI, IP not whitelisted).
        _client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,   # 5 s connection timeout
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
        )

        # Force an actual network round-trip to verify the connection.
        _client.admin.command("ping")
        print("[DB] Connected to MongoDB Atlas successfully.")

    except ServerSelectionTimeoutError as e:
        print(
            f"[DB] FATAL: Could not reach MongoDB Atlas within timeout.\n"
            f"       Check your MONGO_URI and that your IP is whitelisted in Atlas.\n"
            f"       Detail: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    except ConfigurationError as e:
        print(
            f"[DB] FATAL: MongoDB URI is malformed or missing credentials.\n"
            f"       Detail: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    except ConnectionFailure as e:
        print(
            f"[DB] FATAL: MongoDB connection failed.\n"
            f"       Detail: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    except Exception as e:
        print(f"[DB] FATAL: Unexpected error during DB initialisation: {e}", file=sys.stderr)
        sys.exit(1)

    # Bind database and collections
    _db = _client["mindease"]

    users_collection           = _db["users"]
    journal_entries_collection = _db["journal_entries"]

    # Ensure indexes exist (idempotent — safe to call on every startup)
    _ensure_indexes()


# ── Index Management ───────────────────────────────────────────────────────

def _ensure_indexes() -> None:
    """
    Create indexes required for correctness and query performance.
    All index creation calls are idempotent — MongoDB skips them if
    an identical index already exists.
    """
    try:
        # users: enforce unique emails
        users_collection.create_index(
            [("email", ASCENDING)],
            unique=True,
            name="idx_users_email_unique",
        )

        # journal_entries: fast lookup of all entries for a user,
        # sorted newest-first (used by the paginated history endpoint).
        journal_entries_collection.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            name="idx_entries_user_date",
        )

        # journal_entries: fast aggregation by risk level per user
        # (used by the /stats endpoint).
        journal_entries_collection.create_index(
            [("user_id", ASCENDING), ("risk", ASCENDING)],
            name="idx_entries_user_risk",
        )

        print("[DB] Indexes verified.")

    except Exception as e:
        # Non-fatal — the app can still run without optimal indexes.
        print(f"[DB] WARNING: Could not create indexes: {e}", file=sys.stderr)


# ── Health Check ───────────────────────────────────────────────────────────

def ping() -> bool:
    """
    Lightweight liveness check.
    Returns True if the database is reachable, False otherwise.
    Used by the GET / health-check route in predict_routes.py.
    """
    if _client is None:
        return False
    try:
        _client.admin.command("ping")
        return True
    except Exception:
        return False
