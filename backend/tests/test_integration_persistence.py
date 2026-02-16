from fastapi.testclient import TestClient
from app.main import app
from app.state_manager import get_state
import json


def test_post_and_get_session_roundtrip():
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
