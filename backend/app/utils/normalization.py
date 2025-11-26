"""Normalization helpers for model outputs.

Provides functions to extract JSON from model responses (including code
fenced JSON) and to recursively normalize a state dict by parsing any JSON
strings found.
"""
from typing import Any
import re
import json


_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.S)


def _extract_json_from_text(text: str) -> Any:
    """Try to extract JSON object/array from text.

    Returns the parsed JSON object if found and valid, otherwise returns
    None.
    """
    if not isinstance(text, str):
        return None

    # 1) Look for a JSON code fence
    m = _CODE_FENCE_RE.search(text)
    if m:
        candidate = m.group(1)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 2) Look for first JSON-like substring starting with { or [ and try to parse
    idx_brace = text.find("{")
    idx_brack = text.find("[")
    starts = [i for i in (idx_brace, idx_brack) if i != -1]
    if starts:
        start = min(starts)
        candidate = text[start:]
        # Try to parse progressively trimming trailing characters if necessary
        try:
            return json.loads(candidate)
        except Exception:
            # As a fallback, attempt to find a balanced JSON substring using a simple stack
            stack = []
            open_char = candidate[0]
            close_char = '}' if open_char == '{' else ']'
            for i, ch in enumerate(candidate):
                if ch == open_char:
                    stack.append(ch)
                elif ch == close_char:
                    stack.pop()
                    if not stack:
                        sub = candidate[: i + 1]
                        try:
                            return json.loads(sub)
                        except Exception:
                            break

    return None


def normalize_value(val: Any) -> Any:
    """Normalize a single value: if it's a string containing JSON, parse it."""
    if isinstance(val, str):
        parsed = _extract_json_from_text(val)
        if parsed is not None:
            return parsed
        # try raw json
        try:
            return json.loads(val)
        except Exception:
            return val
    if isinstance(val, dict):
        return normalize_state(val)
    if isinstance(val, list):
        return [normalize_value(v) for v in val]
    return val


def normalize_state(state: Any) -> Any:
    """Recursively walk `state` and parse any JSON strings into Python types.

    This returns a new normalized structure.
    """
    if isinstance(state, dict):
        out = {}
        for k, v in state.items():
            out[k] = normalize_value(v)
        return out
    if isinstance(state, list):
        return [normalize_value(v) for v in state]
    return normalize_value(state)
