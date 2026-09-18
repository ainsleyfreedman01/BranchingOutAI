from fastapi.testclient import TestClient
from app.main import AuthenticatedUser, app, authenticated_user
import pytest


@pytest.mark.integration
def test_post_and_get_session_roundtrip(monkeypatch):
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser(
        id="integration-test-user", access_token="test-access-token"
    )
    saved = {}

    def fake_get_state(session_id, user_id=None, access_token=None):
        return saved.get((user_id, session_id), {})

    def fake_save_state(session_id, state, user_id=None, access_token=None):
        saved[(user_id, session_id)] = state

    monkeypatch.setattr("app.main.get_state", fake_get_state)
    monkeypatch.setattr("app.main.save_state", fake_save_state)
    client = TestClient(app)
    sid = "int-test-1"

    # Post a chat input
    resp = client.post("/chatbot/", json={"session_id": sid, "user_input": "I like design"})
    assert resp.status_code == 200
    body = resp.json()
    assert "state" in body
    assert body["state"]["user_input"] == "I like design"

    # Now fetch saved session
    get_resp = client.get(f"/session/{sid}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["session_id"] == sid
    # ensure returned state includes normalized industries list
    assert "industries" in data["state"]
    assert isinstance(data["state"]["industries"], list)
    app.dependency_overrides.clear()
