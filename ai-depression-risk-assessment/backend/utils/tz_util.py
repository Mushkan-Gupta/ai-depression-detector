"""
utils/tz_util.py — Indian Standard Time (IST, UTC+5:30) Utilities
-----------------------------------------------------------------
Centralises all date and time operations so that timestamps across the
entire application conform to Indian Standard Time (Asia/Kolkata).
"""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

try:
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def now_ist() -> datetime:
    """Return the current datetime in Indian Standard Time (IST, UTC+5:30)."""
    return datetime.now(IST)


def to_ist(dt: datetime | None) -> datetime | None:
    """
    Convert a datetime to Indian Standard Time (IST).
    If dt is naive (as stored by PyMongo BSON), it is assumed to be UTC and converted to IST.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def to_ist_iso(dt: datetime | str | None) -> str:
    """
    Return an ISO 8601 string representation in Indian Standard Time (IST).
    """
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    if isinstance(dt, datetime):
        return to_ist(dt).isoformat()
    return str(dt)
