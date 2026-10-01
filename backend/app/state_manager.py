"""State manager with durable Supabase persistence and a local-only fallback.

Uses `get_supabase()` from `app.config`. Calls without an access token may use
in-memory state for local development; authenticated calls fail closed when
Supabase is unavailable or returns an error.
"""

from typing import Dict, Any
from app.config import get_supabase
from app.utils.normalization import normalize_state
import logging

logger = logging.getLogger(__name__)


_memory_store: Dict[str, Dict[str, Any]] = {}


class StatePersistenceUnavailable(RuntimeError):
    """Raised when an authenticated session cannot reach durable storage."""


def _memory_key(session_id: str, user_id: str | None) -> str:
    return f"{user_id}:{session_id}" if user_id is not None else session_id


def _supabase_client(access_token: str | None = None):
    """Get Supabase client or None if not configured.

    Passing the caller's `access_token` authenticates PostgREST requests as
    that user, which Row Level Security policies require to allow access.
    """
    return get_supabase(access_token=access_token)


def _get_supabase_client(access_token: str | None):
    if access_token is None:
        return _supabase_client()
    return _supabase_client(access_token)


def get_state(session_id: str, user_id: str | None = None, access_token: str | None = None) -> Dict[str, Any]:
    """Get state from Supabase or in-memory dict.
    
    Args:
        session_id (str): The user's session ID.
        
    Returns:
        dict: The session state.
    """
    if access_token is None:
        return _memory_store.get(_memory_key(session_id, user_id), {})
    sb = _get_supabase_client(access_token)
    if sb is None:
        raise StatePersistenceUnavailable("Supabase is unavailable for authenticated session access")
    try:
        # Avoid using `.single()` which raises when there are 0 rows.
        # If a user_id is provided, prefer user-scoped row; if not found, fall back
        # to any session-level row (useful if session existed before a user_id was set).
        if user_id is not None:
            query = sb.table("session_states").select("*").eq("session_id", session_id).eq("user_id", user_id)
            res = query.execute()
            data = getattr(res, "data", None)
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("state", {}) or {}
            if isinstance(data, dict) and data.get("state") is not None:
                return data.get("state") or {}
            return {}
        query = sb.table("session_states").select("*").eq("session_id", session_id)
        res = query.execute()
        data = getattr(res, "data", None)
        if isinstance(data, list):
            if len(data) == 0:
                return {}
            return data[0].get("state", {}) or {}
        if isinstance(data, dict):
            return data.get("state", {}) or {}
        return {}
    except Exception:
        logger.exception("get_state: Supabase query failed for session_id=%s", session_id)
        raise StatePersistenceUnavailable("Unable to load session state") from None


def save_state(session_id: str, state: Dict[str, Any], user_id: str | None = None, access_token: str | None = None) -> None:
    """Save state to Supabase or in-memory dict.
    
    Args:
        session_id (str): The user's session ID.
        state (dict): The session state to save.
    """
    # Normalize state (parse JSON strings into structures) before saving.
    normalized = normalize_state(state)

    if access_token is None:
        # persist to in-memory store; attach user_id if present
        entry = dict(normalized)
        if user_id is not None:
            entry.setdefault("user_id", user_id)
        _memory_store[_memory_key(session_id, user_id)] = entry
        return
    sb = _get_supabase_client(access_token)
    if sb is None:
        raise StatePersistenceUnavailable("Supabase is unavailable for authenticated session access")
    payload = {"session_id": session_id, "state": normalized}
    if user_id is not None:
        payload["user_id"] = user_id

    try:
        # session_id is globally unique; RLS prevents an upsert from modifying
        # a row owned by another authenticated user.
        sb.table("session_states").upsert(payload, on_conflict="session_id").execute()
    except Exception as exc:
        logger.exception("save_state: Supabase write failed for session_id=%s", session_id)
        raise StatePersistenceUnavailable("Unable to save session state") from exc