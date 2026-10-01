"""Shared API rate limiting backed by an atomic Supabase/Postgres function."""

import hashlib
import hmac
import os
from typing import Any

from app.config import get_supabase_admin


class RateLimitUnavailable(RuntimeError):
    """Raised when the shared rate-limit store cannot make a decision."""


class SupabaseRateLimiter:
    def __init__(self, client_factory=get_supabase_admin):
        self._client_factory = client_factory

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not service_role_key:
            raise RateLimitUnavailable("Shared rate limiting is not configured")

        opaque_key = hmac.new(
            service_role_key.encode(),
            key.encode(),
            hashlib.sha256,
        ).hexdigest()
        try:
            client = self._client_factory()
            if client is None:
                raise ValueError("Admin client is unavailable")
            response = client.rpc(
                "consume_api_rate_limit",
                {
                    "p_key": opaque_key,
                    "p_limit": limit,
                    "p_window_seconds": window_seconds,
                },
            ).execute()
            result: Any = response.data
            if isinstance(result, list):
                result = result[0] if result else None
            if (
                not isinstance(result, dict)
                or not isinstance(result.get("allowed"), bool)
                or not isinstance(result.get("retry_after"), int)
            ):
                raise ValueError("Rate-limit RPC returned an invalid result")
            return result["allowed"], max(0, result["retry_after"])
        except Exception as exc:
            raise RateLimitUnavailable("Shared rate-limit check failed") from exc