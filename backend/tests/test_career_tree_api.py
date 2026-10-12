from fastapi.testclient import TestClient
from copy import deepcopy

import app.config as config
import app.main as main
from app.main import AuthenticatedUser, app, authenticated_user
from app.career_tree import initialize_tree


def test_tree_routes_persist_and_cache_generated_branch(monkeypatch):
    state = {"skills": ["Python"]}
    saves = []
    calls = []
    monkeypatch.setattr(main, "get_state", lambda *args, **kwargs: state)
    monkeypatch.setattr(main, "save_state", lambda *args, **kwargs: saves.append(args[1]))
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))

    def fake_chat(messages):
        calls.append(messages)
        if "extract up to 6 distinct interests" in messages[-1]["content"].lower():
            return '["Software & AI"]'
        if "Review career branch relevance" in messages[0]["content"]:
            return {"accepted_indices": [0]}
        return '{"children":[{"label":"Technology","why_fit":"Builds software and AI systems.","description":"Builds digital products.","skills":["Python"]}]}'

    monkeypatch.setattr(config.client, "chat", fake_chat)
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser("tree-user", "test-token")

    try:
        client = TestClient(app)
        initialized = client.post("/career-tree/initialize", json={
            "session_id": "tree-session",
            "root_label": "Avery",
            "user_input": "I like software and artificial intelligence",
            "profile_context": {"education": "Design degree"},
        })
        assert initialized.status_code == 200
        tree = initialized.json()["tree"]
        assert [node["type"] for node in tree["nodes"]] == ["user", "interest"]
        assert initialized.json()["response"].startswith("I found these interests")
        assert tree["profileContext"]["skills"] == ["Python"]

        expanded = client.post("/career-tree/expand", json={
            "session_id": "tree-session",
            "node_id": "interest:software-ai",
        })
        assert expanded.status_code == 200
        tree = expanded.json()["tree"]
        assert any(node["label"] == "Technology" for node in tree["nodes"])
        assert saves[-1]["career_tree"]["expandedNodeIds"] == ["you", "interest:software-ai"]

        collapsed = client.put("/career-tree/state", json={
            "session_id": "tree-session",
            "selected_node_id": "interest:software-ai",
            "expanded_node_ids": ["you"],
        })
        assert collapsed.status_code == 200
        reopened = client.post("/career-tree/expand", json={
            "session_id": "tree-session",
            "node_id": "interest:software-ai",
        })
        assert reopened.status_code == 200
        expansion_calls = [call for call in calls if "generate 3-5 distinct" in call[-1]["content"].lower()]
        assert len(expansion_calls) == 1
        assert len([node for node in reopened.json()["tree"]["nodes"] if node["label"] == "Technology"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_profile_interests_seed_tree_without_generating_deeper_nodes(monkeypatch):
    state = {}
    monkeypatch.setattr(main, "get_state", lambda *args, **kwargs: state)
    monkeypatch.setattr(main, "save_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))
    monkeypatch.setattr(config.client, "chat", lambda **kwargs: (_ for _ in ()).throw(AssertionError("AI should not run")))
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser("profile-user", "test-token")

    try:
        response = TestClient(app).post("/career-tree/initialize", json={
            "session_id": "profile-session",
            "root_label": "Avery",
            "profile_context": {"interests": ["Data & Analytics", "Design"]},
        })
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    tree = response.json()["tree"]
    assert [node["type"] for node in tree["nodes"]] == ["user", "interest", "interest"]


def test_reset_clears_graph_state_but_keeps_unrelated_session_state(monkeypatch):
    state = {
        "career_tree": {"nodes": ["old"]},
        "interests": ["Software"],
        "career_paths": ["Engineer"],
        "chat_history": [{"role": "user", "content": "old message"}],
        "unrelated_setting": "keep",
    }
    saves = []
    monkeypatch.setattr(main, "get_state", lambda *args, **kwargs: state)
    monkeypatch.setattr(main, "save_state", lambda *args, **kwargs: saves.append(args[1].copy()))
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser("reset-user", "test-token")

    try:
        response = TestClient(app).post("/career-tree/reset", json={"session_id": "reset-session"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "reset"}
    assert saves == [{"unrelated_setting": "keep"}]


def test_delete_route_persists_and_reload_retains_deletion(monkeypatch):
    state = {"career_tree": initialize_tree("Avery", ["Design", "Data"]), "interests": ["Design", "Data"], "setting": "keep"}
    saves = []
    monkeypatch.setattr(main, "get_state", lambda *args, **kwargs: state)
    monkeypatch.setattr(main, "save_state", lambda *args, **kwargs: saves.append((args[1].copy(), kwargs)))
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser("delete-user", "test-token")
    try:
        client = TestClient(app)
        protected = client.post("/career-tree/delete", json={"session_id": "delete-session", "node_id": "you"})
        assert protected.status_code == 400
        missing = client.post("/career-tree/delete", json={"session_id": "delete-session", "node_id": "missing"})
        assert missing.status_code == 404
        assert saves == []
        deleted = client.post("/career-tree/delete", json={"session_id": "delete-session", "node_id": "interest:design"})
        assert deleted.status_code == 200
        assert [node["id"] for node in deleted.json()["tree"]["nodes"]] == ["you", "interest:data"]
        reloaded = client.get("/session/delete-session").json()["state"]
        assert reloaded["career_tree"] == deleted.json()["tree"]
        assert reloaded["interests"] == ["Data"]
        assert reloaded["setting"] == "keep"
        assert saves[0][1] == {"user_id": "delete-user", "access_token": "test-token"}
    finally:
        app.dependency_overrides.clear()


def test_delete_route_requires_authentication(monkeypatch):
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))
    response = TestClient(app).post("/career-tree/delete", json={"session_id": "delete-session", "node_id": "you"})
    assert response.status_code == 401


def test_opening_account_rebuilds_legacy_graph_once_without_losing_other_state(monkeypatch):
    tree = initialize_tree("Avery", ["Jewish Studies", "Software"], {"skills": ["Writing"]})
    tree.pop("generationVersion")
    tree["nodes"].append({"id": "old-tech", "type": "industry", "label": "Technology", "details": {}})
    tree["edges"].append({"id": "old-edge", "source": "interest:jewish-studies", "target": "old-tech"})
    state = {"career_tree": tree, "chat_history": [{"role": "user", "content": "My interests"}], "setting": "keep"}
    original = deepcopy(state)
    saves = []
    monkeypatch.setattr(main, "get_account_graph_session", lambda *args: ("career-graph:user", state))
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))

    def save(session_id, updated, **kwargs):
        saves.append((session_id, kwargs))
        state.clear()
        state.update(deepcopy(updated))

    monkeypatch.setattr(main, "save_state", save)
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser("user", "test-token")
    try:
        client = TestClient(app)
        first = client.get("/career-tree/session")
        second = client.get("/career-tree/session")
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        rebuilt = first.json()["state"]
        assert [node["type"] for node in rebuilt["career_tree"]["nodes"]] == ["user", "interest", "interest"]
        assert rebuilt["chat_history"] == original["chat_history"]
        assert rebuilt["setting"] == "keep"
        assert rebuilt["career_tree"]["profileContext"] == original["career_tree"]["profileContext"]
        assert "rebuildNotice" in rebuilt["career_tree"]
        assert saves == [("career-graph:user", {"user_id": "user", "access_token": "test-token"})]
    finally:
        app.dependency_overrides.clear()


def test_failed_relevance_check_does_not_persist_or_cache_suggestions(monkeypatch):
    tree = initialize_tree("Avery", ["Jewish Studies"])
    original = deepcopy(tree)
    state = {"career_tree": tree}
    saves = []
    monkeypatch.setattr(main, "get_state", lambda *args, **kwargs: state)
    monkeypatch.setattr(main, "save_state", lambda *args, **kwargs: saves.append(args[1]))
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))

    def fake_chat(messages):
        if "Review career branch relevance" in messages[0]["content"]:
            return {"accepted_indices": []}
        return {"children": [{"label": "Technology", "why_fit": "Generic computer use"}]}

    monkeypatch.setattr(config.client, "chat", fake_chat)
    app.dependency_overrides[authenticated_user] = lambda: AuthenticatedUser("user", "test-token")
    try:
        response = TestClient(app).post("/career-tree/expand", json={
            "session_id": "career-graph:user", "node_id": "interest:jewish-studies",
        })
        assert response.status_code == 502
        assert saves == []
        assert state["career_tree"] == original
    finally:
        app.dependency_overrides.clear()