"""
In-memory pending confirmation store (Phase 2C Step 2a).

WHY in-memory:
  Confirmations are temporary (5-minute timeout). They don't need to survive
  server restarts. If the server restarts, the user can simply re-issue their
  request. This avoids adding a database table for transient state.

Store layout:
  {session_id: {
      "user_id": str,
      "state": dict,             # saved AgentState at confirmation point
      "confirmation_context": {  # for SSE event and UI display
          "title": str,
          "description": str,
          "impact": str,
          "affected_data": dict,
      },
      "confirmation_target": str,
      "created_at": float,       # Unix timestamp
      "expires_at": float,       # Unix timestamp (created_at + 300s)
  }}

Safety:
  - One pending confirmation per session
  - New confirmation replaces old one for the same session
  - Expired entries are cleaned lazily on access
"""

import time
from typing import Optional

# Default timeout: 5 minutes
DEFAULT_TIMEOUT_SECONDS = 300

# Module-level store
_store: dict[str, dict] = {}


# =========================================================================
# Public API
# =========================================================================


def save_pending(
    session_id: str,
    user_id: str,
    state: dict,
    confirmation_target: str,
    confirmation_context: dict,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """
    Save a pending confirmation state.

    Overwrites any existing pending confirmation for the same session.
    """
    now = time.time()
    _store[session_id] = {
        "user_id": user_id,
        "state": state,
        "confirmation_target": confirmation_target,
        "confirmation_context": confirmation_context,
        "created_at": now,
        "expires_at": now + timeout_seconds,
    }


def get_pending(session_id: str) -> Optional[dict]:
    """
    Retrieve a pending confirmation by session_id.

    Returns None if:
      - No pending confirmation for this session
      - The confirmation has expired

    Expired entries are automatically cleaned up.
    """
    entry = _store.get(session_id)
    if entry is None:
        return None

    if time.time() > entry["expires_at"]:
        del _store[session_id]
        return None

    return entry


def delete_pending(session_id: str) -> bool:
    """
    Remove a pending confirmation.

    Returns True if an entry was deleted, False if none existed.
    """
    if session_id in _store:
        del _store[session_id]
        return True
    return False


def is_expired(session_id: str) -> bool:
    """Check if a specific session's confirmation has expired."""
    entry = _store.get(session_id)
    if entry is None:
        return False  # not found ≠ expired
    return time.time() > entry["expires_at"]


def get_store_size() -> int:
    """Return the number of currently pending confirmations (for monitoring)."""
    # Clean expired entries first
    now = time.time()
    expired = [sid for sid, e in _store.items() if now > e["expires_at"]]
    for sid in expired:
        del _store[sid]
    return len(_store)
