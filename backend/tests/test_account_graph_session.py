from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.main as main
import app.state_manager as state_manager


class SessionTable:
    def __init__(self, rows):
        self.rows = rows
        self.filters = {}
        self.pending = None
        self.before_insert = None

    def select(self, columns):
        self.filters = {}
        self.pending = None
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def upsert(self, payload, on_conflict, ignore_duplicates):
        assert on_conflict == "session_id"
        assert ignore_duplicates
        self.pending = deepcopy(payload)
        return self

    def execute(self):
        if self.pending:
            if self.before_insert:
                self.rows.append(self.before_insert)
                self.before_insert = None
            if not any(row["session_id"] == self.pending["session_id"] for row in self.rows):
                self.rows.append(self.pending)
            self.pending = None
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=deepcopy([
            row for row in self.rows
            if all(row.get(key) == value for key, value in self.filters.items())
        ]))


def install_store(monkeypatch, rows):
    table = SessionTable(rows)
    monkeypatch.setattr(
        state_manager, "_supabase_client",
        lambda access_token: SimpleNamespace(table=lambda name: table),
    )
    return table


def test_browsers_adopt_existing_tree_without_overwriting_legacy_saves(monkeypatch):
    saved = {"career_tree": {"nodes": [{"id": "you"}, {"id": "ai"}]}, "interests": ["AI"]}
    rows = [
        {"session_id": "empty-preview", "user_id": "user-a", "state": {}},
        {"session_id": "browser-graph", "user_id": "user-a", "state": saved},
        {"session_id": "private-graph", "user_id": "user-b", "state": {"private": True}},
    ]
    install_store(monkeypatch, rows)
    first = state_manager.get_account_graph_session("user-a", "token-a")
    second = state_manager.get_account_graph_session("user-a", "token-a")
    assert first == second == ("career-graph:user-a", saved)
    assert len(rows) == 4
    assert rows[1]["state"] == saved


def test_reset_account_graph_does_not_resurrect_legacy_tree(monkeypatch):
    install_store(monkeypatch, [
        {"session_id": "legacy", "user_id": "user-a", "state": {"career_tree": {"nodes": [1, 2]}}},
        {"session_id": "career-graph:user-a", "user_id": "user-a", "state": {}},
    ])
    assert state_manager.get_account_graph_session("user-a", "token-a") == ("career-graph:user-a", {})


def test_new_accounts_are_isolated_and_concurrent_creation_keeps_winner(monkeypatch):
    rows = []
    table = install_store(monkeypatch, rows)
    winner = {"interests": ["Design"]}
    table.before_insert = {"session_id": "career-graph:user-a", "user_id": "user-a", "state": winner}
    assert state_manager.get_account_graph_session("user-a", "token-a") == ("career-graph:user-a", winner)
    assert state_manager.get_account_graph_session("user-b", "token-b") == ("career-graph:user-b", {})
    assert len(rows) == 2


def test_account_session_route_uses_authenticated_owner_and_fails_explicitly(monkeypatch):
    calls = []
    monkeypatch.setattr(main.rate_limiter, "allow", lambda *args: (True, 0))
    monkeypatch.setattr(main, "get_account_graph_session", lambda *args: (
        calls.append(args) or ("career-graph:user-a", {"interests": ["AI"]})
    ))
    client = TestClient(main.app)
    assert client.get("/career-tree/session").status_code == 401
    main.app.dependency_overrides[main.authenticated_user] = lambda: main.AuthenticatedUser("user-a", "token-a")
    try:
        response = client.get("/career-tree/session")
        assert response.status_code == 200
        assert response.json() == {"session_id": "career-graph:user-a", "state": {"interests": ["AI"]}}
        assert calls == [("user-a", "token-a")]

        def unavailable(*args):
            raise state_manager.StatePersistenceUnavailable("storage offline")

        monkeypatch.setattr(main, "get_account_graph_session", unavailable)
        assert client.get("/career-tree/session").status_code == 503
    finally:
        main.app.dependency_overrides.clear()


def test_account_lookup_does_not_fall_back_when_storage_unavailable(monkeypatch):
    monkeypatch.setattr(state_manager, "_supabase_client", lambda access_token: None)
    with pytest.raises(state_manager.StatePersistenceUnavailable):
        state_manager.get_account_graph_session("user-a", "token-a")
