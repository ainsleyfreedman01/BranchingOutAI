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


def test_save_state_calls_supabase_insert_and_update(monkeypatch):
    # Fake supabase client that records insert/update data
    class FakeTable:
        def __init__(self):
            self.inserted = None
            self.updated = None

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def single(self):
            return self

        def execute(self):
            return types.SimpleNamespace(data=None)

        def update(self, payload):
            self.updated = payload
            return self

        def insert(self, payload):
            self.inserted = payload
            return self

    class FakeClient:
        def __init__(self, table_obj):
            self._table = table_obj

        def table(self, name):
            return self._table

    fake_table = FakeTable()
    fake_client = FakeClient(fake_table)

    import app.state_manager as sm
    monkeypatch.setattr(sm, "_supabase_client", lambda: fake_client)

    raw = {"interests": '{"a":1, "b":[2,3]}'}
    session_id = "test-sb-1"

    save_state(session_id, raw)

    # For new insert, FakeTable.insert should have been called with normalized state
    assert fake_table.inserted is not None
    assert isinstance(fake_table.inserted["state"], dict)
    assert fake_table.inserted["state"]["interests"]["a"] == 1


def test_save_state_update_existing(monkeypatch):
    # Simulate an existing row so save_state should call update
    class FakeTableExisting:
        def __init__(self):
            self.inserted = None
            self.updated = None

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def single(self):
            return self

        def execute(self):
            # Return existing data to indicate the row exists
            return types.SimpleNamespace(data={"state": {"interests": {"a": 0}}})

        def update(self, payload):
            self.updated = payload
            return self

        def insert(self, payload):
            self.inserted = payload
            return self

    class FakeClientExisting:
        def __init__(self, table_obj):
            self._table = table_obj

        def table(self, name):
            return self._table

    fake_table = FakeTableExisting()
    fake_client = FakeClientExisting(fake_table)

    import app.state_manager as sm
    monkeypatch.setattr(sm, "_supabase_client", lambda: fake_client)

    raw = {"interests": '{"a":1, "b":[2,3]}'}
    session_id = "test-sb-2"

    save_state(session_id, raw)

    # Since the row existed, update should be called with normalized state
    assert fake_table.updated is not None
    assert fake_table.updated["state"]["interests"]["a"] == 1
