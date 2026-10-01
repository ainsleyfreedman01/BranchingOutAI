import types
from app.state_manager import save_state, _memory_store


def test_save_state_in_memory_normalizes(monkeypatch):
    # Ensure get_supabase returns None to force in-memory path
    import app.state_manager as sm

    monkeypatch.setattr(sm, "_supabase_client", lambda: None)

    # raw state includes a code-fenced JSON string
    raw = {"skills": "Results:\n```json\n{\"hard\": [\"py\"], \"soft\": [\"comm\"]}\n```"}
    session_id = "test-memory-1"
    # clear store
    if session_id in _memory_store:
        del _memory_store[session_id]

    save_state(session_id, raw)

    saved = _memory_store.get(session_id)
    assert isinstance(saved, dict)
    assert isinstance(saved.get("skills"), dict)
    assert saved["skills"]["hard"] == ["py"]


def test_save_state_uses_atomic_supabase_upsert(monkeypatch):
    # Fake Supabase client that records atomic upsert data.
    class FakeTable:
        def __init__(self):
            self.upserted = None
            self.conflict_target = None

        def upsert(self, payload, on_conflict=None):
            self.upserted = payload
            self.conflict_target = on_conflict
            return self

        def execute(self):
            return types.SimpleNamespace(data=[self.upserted])

    fake_table = FakeTable()
    fake_client = type("FakeClient", (), {"table": lambda self, name: fake_table})()

    import app.state_manager as sm
    monkeypatch.setattr(sm, "_supabase_client", lambda access_token=None: fake_client)

    raw = {"interests": '{"a":1, "b":[2,3]}'}
    session_id = "test-sb-1"

    save_state(session_id, raw, user_id="test-user", access_token="test-token")

    assert fake_table.conflict_target == "session_id"
    assert fake_table.upserted["session_id"] == session_id
    assert fake_table.upserted["state"]["interests"]["a"] == 1


def test_save_state_upserts_existing_rows_without_read_then_write(monkeypatch):
    class FakeTable:
        def __init__(self):
            self.upserted = None

        def upsert(self, payload, on_conflict=None):
            self.upserted = payload
            return self

        def execute(self):
            return types.SimpleNamespace(data=[self.upserted])

    fake_table = FakeTable()
    fake_client = type("FakeClient", (), {"table": lambda self, name: fake_table})()

    import app.state_manager as sm
    monkeypatch.setattr(sm, "_supabase_client", lambda access_token=None: fake_client)

    session_id = "test-sb-1"
    save_state(
        session_id,
        {"interests": '{"a":1, "b":[2,3]}'},
        user_id="test-user",
        access_token="test-token",
    )

    assert fake_table.upserted["session_id"] == session_id
    assert fake_table.upserted["state"]["interests"]["a"] == 1
