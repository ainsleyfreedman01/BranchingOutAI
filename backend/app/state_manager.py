"""State manager with optional Supabase persistence and in-memory fallback.

Uses `get_supabase()` from `app.config`. If Supabase is not configured, keeps
session state in an in-memory dict for the process lifetime.
"""

from typing import Dict, Any
from app.config import get_supabase
from app.utils.normalization import normalize_state
import logging

logger = logging.getLogger(__name__)


_memory_store: Dict[str, Dict[str, Any]] = {}


def _supabase_client():
    """Get Supabase client or None if not configured."""
    return get_supabase()


def get_state(session_id: str, user_id: str | None = None) -> Dict[str, Any]:
    """Get state from Supabase or in-memory dict.
    
    Args:
        session_id (str): The user's session ID.
        
    Returns:
        dict: The session state.
    """
    sb = _supabase_client()
    if sb is None:
        return _memory_store.get(session_id, {})
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
            # fallback to session-only row
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
        # If Supabase is misconfigured, log the error and fall back to memory
        logger.exception("get_state: Supabase query failed for session_id=%s", session_id)
        return _memory_store.get(session_id, {})


def save_state(session_id: str, state: Dict[str, Any], user_id: str | None = None) -> None:
    """Save state to Supabase or in-memory dict.
    
    Args:
        session_id (str): The user's session ID.
        state (dict): The session state to save.
    """
    # Normalize state (parse JSON strings into structures) before saving.
    normalized = normalize_state(state)

    sb = _supabase_client()
    if sb is None:
        # persist to in-memory store; attach user_id if present
        if user_id is not None:
            entry = dict(normalized)
            entry.setdefault("user_id", user_id)
            _memory_store[session_id] = entry
        else:
            _memory_store[session_id] = normalized
        return
    try:
        # Prefer a single upsert call when supported by the client to avoid
        # races and multiple round-trips. Build an insert payload and only
        # include `user_id` when provided.
        insert_payload = {"session_id": session_id, "state": normalized}
        if user_id is not None:
            insert_payload["user_id"] = user_id

        # Many supabase clients expose `.upsert()`; if available this will
        # create-or-update the row atomically based on primary/unique keys.
        try:
            sb.table("session_states").upsert(insert_payload).execute()
            return
        except Exception:
            # Fall back to select->update/insert behavior if upsert isn't
            # supported or fails for any reason.
            logger.debug("save_state: upsert failed, falling back to select/update/insert")

        # Check for existing row by session_id and update or insert accordingly.
        res = sb.table("session_states").select("*").eq("session_id", session_id).execute()
        existing = getattr(res, "data", None)

        payload = {"state": normalized}
        if user_id is not None:
            payload["user_id"] = user_id

        if isinstance(existing, list) and len(existing) > 0:
            sb.table("session_states").update(payload).eq("session_id", session_id).execute()
        elif isinstance(existing, dict) and existing.get("state") is not None:
            sb.table("session_states").update(payload).eq("session_id", session_id).execute()
        else:
            sb.table("session_states").insert(insert_payload).execute()
    except Exception:
        # If Supabase is misconfigured or the table is missing, log and persist to memory instead
        logger.exception("save_state: Supabase write failed for session_id=%s", session_id)
        if user_id is not None:
            entry = dict(normalized)
            entry.setdefault("user_id", user_id)
            _memory_store[session_id] = entry
        else:
            _memory_store[session_id] = normalized