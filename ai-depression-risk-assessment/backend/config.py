"""
config.py — Centralised Environment Configuration
--------------------------------------------------
Loads all environment variables from the .env file and exposes
them as a typed Config class consumed by app.py and other modules.

Usage:
    from config import Config
    app.config.from_object(Config)
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Resolve the absolute path to the .env file sitting next to this file.
# This ensures .env is found regardless of where the server is launched from.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH  = os.path.join(_BASE_DIR, ".env")

load_dotenv(_ENV_PATH)


# ── Helpers ────────────────────────────────────────────────────────────────

def _require(key: str) -> str:
    """Read a required env variable; raise a clear error if it is missing."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"[CONFIG] Required environment variable '{key}' is not set. "
            f"Check your .env file at: {_ENV_PATH}"
        )
    return value


def _optional(key: str, default: str = "") -> str:
    """Read an optional env variable, returning a default if absent."""
    return os.getenv(key, default)


# ── Configuration Class ────────────────────────────────────────────────────

class Config:
    """
    Flask-compatible configuration class.

    All attributes are read once at import time.  flask-jwt-extended,
    PyMongo, and Flask itself consume these via app.config.from_object().
    """

    # ── MongoDB ─────────────────────────────────────────────────────────
    MONGO_URI: str = _require("MONGO_URI")

    # ── JWT ─────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str        = _require("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES   = timedelta(days=7)   # tokens valid for 7 days
    JWT_TOKEN_LOCATION         = ["headers"]          # look for Bearer token in headers
    JWT_HEADER_NAME            = "Authorization"
    JWT_HEADER_TYPE            = "Bearer"

    # ── Flask ────────────────────────────────────────────────────────────
    # Never enable DEBUG in production; default to False for safety.
    DEBUG: bool = _optional("DEBUG", "False").lower() == "true"

    # ── Server ───────────────────────────────────────────────────────────
    PORT: int = int(_optional("PORT", "5000"))

    # ── CORS ─────────────────────────────────────────────────────────────
    # Restrict origins in production via the ALLOWED_ORIGINS env variable.
    # Example: ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
    # Defaults to "*" for local development only.
    ALLOWED_ORIGINS: list = [
        origin.strip()
        for origin in _optional("ALLOWED_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    # ── Pagination ───────────────────────────────────────────────────────
    HISTORY_PAGE_SIZE: int = int(_optional("HISTORY_PAGE_SIZE", "10"))

    # ── Google OAuth ──────────────────────────────────────────────────────
    # GOOGLE_CLIENT_ID is required for server-side ID-token verification.
    # GOOGLE_CLIENT_SECRET is kept for completeness but not used in the
    # stateless GIS sign-in flow (no server-side OAuth code exchange needed).
    GOOGLE_CLIENT_ID: str     = _require("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = _optional("GOOGLE_CLIENT_SECRET", "")
