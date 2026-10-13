from fastapi.testclient import TestClient
from app.main import AuthenticatedUser, app, authenticated_user
import pytest


@pytest.mark.integration
def test_initialize_and_get_session_roundtrip(monkeypatch):
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser(
        id="integration-test-user", access_token="test-access-token"
    )
    monkeypatch.setattr("app.main.rate_limiter.allow", lambda *args: (True, 0))
    monkeypatch.setattr("app.config.client.chat", lambda *args, **kwargs: "unused")
    saved = {}

    def fake_get_state(session_id, user_id=None, access_token=None):
        return saved.get((user_id, session_id), {})

    def fake_save_state(session_id, state, user_id=None, access_token=None):
        saved[(user_id, session_id)] = state

    monkeypatch.setattr("app.main.get_state", fake_get_state)
    monkeypatch.setattr("app.main.save_state", fake_save_state)
    client = TestClient(app)
    sid = "int-test-1"

    resp = client.post("/career-tree/initialize", json={
        "session_id": sid,
        "root_label": "Avery",
        "profile_context": {"interests": ["Design"]},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "tree" in body
    assert [node["label"] for node in body["tree"]["nodes"]] == ["Avery", "Design"]

    # Now fetch saved session
    get_resp = client.get(f"/session/{sid}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["session_id"] == sid
    assert data["state"]["career_tree"] == body["tree"]
    assert data["state"]["interests"] == ["Design"]
    app.dependency_overrides.clear()
