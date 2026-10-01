from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

import app.config as config
import app.main as main
from app.rate_limiter import RateLimitUnavailable, SupabaseRateLimiter
from app.main import AuthenticatedUser, app, authenticated_user, validate_runtime_settings
from app.state_manager import StatePersistenceUnavailable


def test_rate_limit_is_shared_across_limiter_instances(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    rows = {}
    calls = []

    class FakeRpc:
        def __init__(self, params):
            self.params = params

        def execute(self):
            calls.append(self.params["p_key"])
            count = rows.get(self.params["p_key"], 0) + 1
            rows[self.params["p_key"]] = count
            allowed = count <= self.params["p_limit"]
            return SimpleNamespace(data=[{"allowed": allowed, "retry_after": 0 if allowed else 12}])

    class FakeClient:
        def rpc(self, name, params):
            assert name == "consume_api_rate_limit"
            return FakeRpc(params)

    client = FakeClient()
    first_worker = SupabaseRateLimiter(client_factory=lambda: client)
    restarted_worker = SupabaseRateLimiter(client_factory=lambda: client)

    assert first_worker.allow("user:user-a", limit=1, window_seconds=60) == (True, 0)
    assert restarted_worker.allow("user:user-a", limit=1, window_seconds=60) == (False, 12)
    assert len(rows) == 1
    assert calls[0] != "user:user-a"


def test_storage_failure_is_returned_as_service_unavailable(monkeypatch):
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser(
        id="storage-failure-user", access_token="test-token"
    )
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))
    monkeypatch.setattr(
        main,
        "get_state",
        lambda *args, **kwargs: (_ for _ in ()).throw(StatePersistenceUnavailable("database down")),
    )

    try:
        response = TestClient(app).post(
            "/chatbot/",
            json={"session_id": "storage-failure-session", "user_input": "design"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Session storage is unavailable"}


def test_ready_reports_missing_supabase(monkeypatch):
    monkeypatch.setattr(config, "get_supabase_admin", lambda: None)

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Supabase is unavailable"}


def _set_production_environment(monkeypatch, origins="https://careers.example.com"):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "public-test-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "server-test-key")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", origins)


def test_production_settings_accept_exact_https_frontend_origin(monkeypatch):
    _set_production_environment(monkeypatch, "https://careers.example.com,https://www.example.com")

    validate_runtime_settings()


def test_production_settings_reject_missing_service_role_key(monkeypatch):
    _set_production_environment(monkeypatch)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY")

    with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_ROLE_KEY"):
        validate_runtime_settings()


@pytest.mark.parametrize("origin", ["http://careers.example.com", "http://localhost:3000", "*"])
def test_production_settings_reject_insecure_cors_origins(monkeypatch, origin):
    _set_production_environment(monkeypatch, origin)

    with pytest.raises(RuntimeError, match="exact HTTPS frontend origins"):
        validate_runtime_settings()


def test_hsts_is_added_only_for_production_https_responses(monkeypatch):
    _set_production_environment(monkeypatch)

    https_response = TestClient(app, base_url="https://testserver").get("/health")
    http_response = TestClient(app, base_url="http://testserver").get("/health")

    assert https_response.headers["Strict-Transport-Security"] == "max-age=31536000"
    assert "Strict-Transport-Security" not in http_response.headers


def test_rate_limit_store_failure_fails_closed(monkeypatch):
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser(
        id="rate-limit-user", access_token="test-token"
    )

    class FailingLimiter:
        def allow(self, key, limit, window_seconds):
            raise RateLimitUnavailable("database unavailable")

    monkeypatch.setattr(main, "rate_limiter", FailingLimiter())
    try:
        response = TestClient(app).get("/session/session-a")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Rate limiting is unavailable"}


def test_rate_limit_rejection_returns_retry_after(monkeypatch):
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser(
        id="rate-limit-user", access_token="test-token"
    )

    class RejectingLimiter:
        def allow(self, key, limit, window_seconds):
            return False, 17

    monkeypatch.setattr(main, "rate_limiter", RejectingLimiter())
    try:
        response = TestClient(app).get("/session/session-a")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "17"


def test_client_ip_limit_runs_before_bearer_authentication(monkeypatch):
    checked_keys = []
    monkeypatch.setattr(
        main.rate_limiter,
        "allow",
        lambda key, limit, window: (checked_keys.append(key) or True, 0),
    )

    response = TestClient(app).get("/session/session-a")

    assert response.status_code == 401
    assert checked_keys == ["ip:testclient"]


def test_ip_quota_rejects_anonymous_request_before_auth(monkeypatch):
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (False, 23))

    response = TestClient(app).get("/session/session-a")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "23"


def test_oversized_request_body_is_rejected_before_route_handling():
    response = TestClient(app).post(
        "/chatbot/",
        content=b"x" * (64 * 1024 + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request body is too large"}


def test_account_deletion_uses_user_cascade(monkeypatch):
    deleted_users = []

    class FakeAdminClient:
        auth = SimpleNamespace(admin=SimpleNamespace(delete_user=deleted_users.append))

        def table(self, name):
            raise AssertionError("account deletion should rely on the database cascade")

    monkeypatch.setattr(config, "get_supabase_admin", lambda: FakeAdminClient())
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser(
        id="delete-user", access_token="test-token"
    )

    try:
        response = TestClient(app).delete("/account")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert deleted_users == ["delete-user"]