import app.career_workflow as career_workflow
from fastapi.testclient import TestClient

from app.main import app


def test_expand_operation_runs_through_compiled_workflow(monkeypatch):
    expected_tree = {"nodes": [{"id": "interest:data"}], "edges": []}
    calls = []

    def fake_expand_tree(tree, node_id, chat):
        calls.append((tree, node_id, chat))
        return expected_tree

    chat = object()
    monkeypatch.setattr(career_workflow, "expand_tree", fake_expand_tree)

    result = career_workflow.run_career_workflow(
        "expand",
        tree={"nodes": [], "edges": []},
        node_id="interest:data",
        chat=chat,
    )

    assert result == expected_tree
    assert calls == [({"nodes": [], "edges": []}, "interest:data", chat)]


def test_legacy_chatbot_route_is_removed():
    response = TestClient(app).post(
        "/chatbot/",
        json={"session_id": "old-session", "user_input": "design"},
    )

    assert response.status_code == 404
