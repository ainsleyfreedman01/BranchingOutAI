from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.config as config
import app.main as main
from app.main import AuthenticatedUser, app, authenticated_user
from app.state_manager import StatePersistenceUnavailable


def test_rate_limiter_expires_idle_keys(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(main.time, "monotonic", lambda: now[0])
    limiter = main.InMemoryRateLimiter()

    assert limiter.allow("old-client", limit=2, window_seconds=5) == (True, 0)
    assert limiter.allow("another-old-client", limit=2, window_seconds=5) == (True, 0)
    now[0] = 6.0

    assert limiter.allow("current-client", limit=2, window_seconds=5) == (True, 0)
    assert list(limiter._requests) == ["current-client"]


def test_storage_failure_is_returned_as_service_unavailable(monkeypatch):
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser(
        id="storage-failure-user", access_token="test-token"
    )
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
    monkeypatch.setattr(config, "get_supabase", lambda: None)

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Supabase is unavailable"}


def test_account_deletion_uses_user_cascade(monkeypatch):
    deleted_users = []

    class FakeAdminClient:
        auth = SimpleNamespace(admin=SimpleNamespace(delete_user=deleted_users.append))

        def table(self, name):
            raise AssertionError("account deletion should rely on the database cascade")

    monkeypatch.setattr(config, "get_supabase_admin", lambda: FakeAdminClient())
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser(
        id="delete-user", access_token="test-token"
    )

    try:
        response = TestClient(app).delete("/account")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert deleted_users == ["delete-user"]