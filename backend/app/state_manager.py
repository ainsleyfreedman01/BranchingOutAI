"""State manager with optional Supabase persistence and in-memory fallback.

Uses `get_supabase()` from `app.config`. If Supabase is not configured, keeps
session state in an in-memory dict for the process lifetime.
"""

from typing import Dict, Any
from app.config import get_supabase


_memory_store: Dict[str, Dict[str, Any]] = {}


def _supabase_client():
    """Get Supabase client or None if not configured."""
    return get_supabase()


def get_state(session_id: str) -> Dict[str, Any]:
    """Get state from Supabase or in-memory dict.
    
    Args:
        session_id (str): The user's session ID.
        
    Returns:
        dict: The session state.
    """
    sb = _supabase_client()
    if sb is None:
        return _memory_store.get(session_id, {})
    res = sb.table("session_states").select("*").eq("session_id", session_id).single().execute()
    if getattr(res, "data", None):
        # some clients return list, some return object with data
        data = res.data
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("state", {})
        if isinstance(data, dict):
            return data.get("state", {})
    return {}


def save_state(session_id: str, state: Dict[str, Any]) -> None:
    """Save state to Supabase or in-memory dict.
    
    Args:
        session_id (str): The user's session ID.
        state (dict): The session state to save.
    """
    sb = _supabase_client()
    if sb is None:
        _memory_store[session_id] = state
        return
    existing = sb.table("session_states").select("*").eq("session_id", session_id).single().execute()
    if getattr(existing, "data", None):
        sb.table("session_states").update({"state": state}).eq("session_id", session_id).execute()
    else:
        sb.table("session_states").insert({"session_id": session_id, "state": state}).execute()