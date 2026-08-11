import os
import sys
import pytest

# Add backend directory to sys.path so we can import app and db
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ── DATABASE REROUTING FOR TESTS ──────────────────────────────────────────────
# Developers: This file automatically intercepts the database connection and
# points it to 'mindease_test'. You do not need to manually change MONGO_URI
# to run tests. It will use the cluster specified by the existing MONGO_URI,
# but guarantee isolation from production data.

# 1. Import the app which internally initializes the db connection (db.init_db)
from app import app as flask_app
import db

# 2. Rebind the db handles to the test database 'mindease_test'
# This works seamlessly because all routes access collections dynamically via `import db as _db`
# and read the module attributes at request time.
db._db = db._client["mindease_test"]
db.users_collection = db._db["users"]
db.journal_entries_collection = db._db["journal_entries"]
db.connection_requests_collection = db._db["connection_requests"]
db.conversations_collection = db._db["conversations"]
db.messages_collection = db._db["messages"]
db.peer_reports_collection = db._db["peer_reports"]


@pytest.fixture(scope="session", autouse=True)
def db_safety_guard():
    """
    CRITICAL SAFETY GUARD:
    Ensure that we are genuinely connected to the 'mindease_test' database.
    If not, hard-fail immediately to prevent any modification to production data.
    """
    if db._db.name != "mindease_test":
        pytest.exit(f"CRITICAL SAFETY GUARD: Connected to '{db._db.name}' instead of 'mindease_test'. Aborting test run to prevent production data modification.")
    
    # Optional: Initial setup could go here.
    yield


@pytest.fixture(scope="function", autouse=True)
def db_cleanup():
    """
    Function-scoped fixture to automatically clean the test database
    before/after every individual test runs. Ensures pristine state.
    """
    # Clean before test
    db.users_collection.delete_many({})
    db.journal_entries_collection.delete_many({})
    db.connection_requests_collection.delete_many({})
    db.conversations_collection.delete_many({})
    db.messages_collection.delete_many({})
    db.peer_reports_collection.delete_many({})
    
    yield
    
    # Clean after test
    db.users_collection.delete_many({})
    db.journal_entries_collection.delete_many({})
    db.connection_requests_collection.delete_many({})
    db.conversations_collection.delete_many({})
    db.messages_collection.delete_many({})
    db.peer_reports_collection.delete_many({})


@pytest.fixture
def app():
    """Yield the configured Flask app instance."""
    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app


@pytest.fixture
def client(app):
    """Yield a test client for the Flask app."""
    return app.test_client()
