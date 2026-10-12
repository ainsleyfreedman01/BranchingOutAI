from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

from app import config, main
from app.career_chat import explain_node, NodeExplanationNotAllowed
from app.career_tree import initialize_tree


def explanation():
    return {
        "overview": "This work involves teaching and designing learning activities.",
        "skills": ["Lesson planning", "Communication"],
        "qualifications": ["Employers often prefer relevant education; licensing varies."],
        "resources": ["Look for educator preparation guidance from your state education department."],
    }


def saved_state():
    tree = initialize_tree("Avery", ["Jewish Studies", "Software"])
    tree["nodes"].extend([
        {"id": "sector", "type": "industry", "label": "Jewish Education", "details": {}},
        {"id": "role", "type": "role", "label": "Jewish Studies Educator",
         "details": {"why_fit": "Teach Jewish history and culture."}},
    ])
    tree["edges"].extend([
        {"id": "s", "source": "interest:jewish-studies", "target": "sector"},
        {"id": "r", "source": "sector", "target": "role"},
    ])
    return {
        "career_tree": tree,
        "chat_history": [{"role": "user", "content": "Previous question"}],
        "pending_career_changes": {"id": "keep", "interests": ["Music"]},
        "other_setting": "unchanged",
    }


@pytest.mark.parametrize("node_id", ["interest:jewish-studies", "sector", "role"])
def test_any_node_explanation_has_four_sections_without_graph_or_proposal_changes(node_id):
    state = saved_state()
    original = deepcopy(state)
    calls = []

    def chat(messages):
        calls.append(messages)
        return json.dumps({**explanation(), "interests_to_add": ["Ignore this extra field"]})

    updated = explain_node(state, node_id, chat)
    assert state == original
    assert updated["career_tree"] == original["career_tree"]
    assert updated["pending_career_changes"] == original["pending_career_changes"]
    assert updated["other_setting"] == "unchanged"
    assert updated["chat_history"][0] == original["chat_history"][0]
    assert updated["chat_history"][-1]["content"] == updated["assistant_response"]
    assert updated["chat_history"][-2]["role"] == "user"
    for heading in ["Overview", "Typical skills", "Typical qualifications", "Ways to build skills and qualifications"]:
        assert f"### {heading}\n\n" in updated["assistant_response"]
    assert "\n- Lesson planning\n- Communication" in updated["assistant_response"]
    assert "\n\n> Requirements vary" in updated["assistant_response"]
    prompt = json.loads(calls[0][-1]["content"])
    assert prompt["selected_node"]["id"] == node_id
    if node_id == "role":
        assert [node["id"] for node in prompt["career_path"]] == ["interest:jewish-studies", "sector", "role"]
        assert "Software" not in calls[0][-1]["content"]
    assert "not URLs" in calls[0][0]["content"]
    assert "requirements vary" in calls[0][0]["content"]


@pytest.mark.parametrize("invalid", [
    {}, {"overview": " "}, {**explanation(), "skills": []},
    {**explanation(), "qualifications": "Degree"}, {**explanation(), "resources": [None]},
    {**explanation(), "overview": "x" * 4000}, "invalid json",
])
def test_invalid_explanations_do_not_modify_saved_state(invalid):
    state = saved_state()
    original = deepcopy(state)
    with pytest.raises(ValueError):
        explain_node(state, "role", lambda **kw: invalid)
    assert state == original


def test_unknown_node_does_not_call_ai():
    def unexpected_call(**kwargs):
        pytest.fail("Unknown nodes must not call AI")

    with pytest.raises(KeyError):
        explain_node(saved_state(), "missing", unexpected_call)


@pytest.mark.parametrize("root_type", ["user", "interest"])
def test_name_node_is_rejected_before_ai_call_without_changing_state(root_type):
    state = saved_state()
    state["career_tree"]["nodes"][0]["type"] = root_type
    original = deepcopy(state)

    def unexpected_call(**kwargs):
        pytest.fail("The central name node must not call AI")

    with pytest.raises(NodeExplanationNotAllowed, match="central name node"):
        explain_node(state, "you", unexpected_call)
    assert state == original


def test_explanation_preserves_bounded_history():
    state = saved_state()
    state["chat_history"] = [{"role": "user", "content": str(i)} for i in range(40)]
    updated = explain_node(state, "role", lambda **kw: explanation())
    assert len(updated["chat_history"]) == 40
    assert updated["chat_history"][0]["content"] == "2"


def test_explain_endpoint_authenticates_persists_and_reports_errors(monkeypatch):
    state = saved_state()
    saved = []
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *a: (True, 0))
    monkeypatch.setattr(main, "get_state", lambda *a, **kw: deepcopy(state))
    monkeypatch.setattr(main, "save_state", lambda session_id, updated, **kw: saved.append((session_id, updated, kw)))
    monkeypatch.setattr(config.client, "chat_json", lambda **kw: explanation())
    client = TestClient(main.app)
    payload = {"session_id": "session", "node_id": "role"}
    assert client.post("/career-tree/explain", json=payload).status_code == 401
    main.app.dependency_overrides[main.authenticated_user] = lambda: main.AuthenticatedUser("user", "token")
    try:
        response = client.post("/career-tree/explain", json=payload)
        assert response.status_code == 200
        assert response.json()["state"]["career_tree"] == state["career_tree"]
        assert response.json()["response"] == response.json()["state"]["assistant_response"]
        assert saved[0][0] == "session"
        assert saved[0][2] == {"user_id": "user", "access_token": "token"}
        root_response = client.post("/career-tree/explain", json={**payload, "node_id": "you"})
        assert root_response.status_code == 400
        assert "central name node" in root_response.json()["detail"]
        assert client.post("/career-tree/explain", json={**payload, "node_id": "missing"}).status_code == 404
        monkeypatch.setattr(config.client, "chat_json", lambda **kw: {})
        assert client.post("/career-tree/explain", json=payload).status_code == 502

        def unavailable(**kw):
            raise RuntimeError("Provider unavailable")

        monkeypatch.setattr(config.client, "chat_json", unavailable)
        assert client.post("/career-tree/explain", json=payload).status_code == 502
        state.clear()
        assert client.post("/career-tree/explain", json=payload).status_code == 409
        assert len(saved) == 1
    finally:
        main.app.dependency_overrides.clear()
