import pytest

import app.state_manager as state_manager


def test_authenticated_read_does_not_fall_back_when_supabase_is_missing(monkeypatch):
    monkeypatch.setattr(state_manager, "_supabase_client", lambda access_token=None: None)

    with pytest.raises(state_manager.StatePersistenceUnavailable):
        state_manager.get_state("session-a", user_id="user-a", access_token="token-a")


def test_authenticated_write_failure_does_not_fall_back_to_memory(monkeypatch):
    class FailingTable:
        def upsert(self, payload, on_conflict=None):
            return self

        def execute(self):
            raise RuntimeError("database unavailable")

    class FakeClient:
        def table(self, name):
            return FailingTable()

    monkeypatch.setattr(state_manager, "_supabase_client", lambda access_token=None: FakeClient())
    state_manager._memory_store.pop("user-a:session-a", None)

    with pytest.raises(state_manager.StatePersistenceUnavailable):
        state_manager.save_state(
            "session-a",
            {"interests": ["design"]},
            user_id="user-a",
            access_token="token-a",
        )

    assert "user-a:session-a" not in state_manager._memory_store