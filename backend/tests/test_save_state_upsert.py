import types
from app.state_manager import save_state


def test_save_state_uses_upsert_when_available(monkeypatch):
    class FakeTableUpsert:
        def __init__(self):
            self.upsert_called = False
            self.upsert_payload = None

        def upsert(self, payload):
            self.upsert_called = True
            self.upsert_payload = payload
            return self

        def execute(self):
            # emulate a successful response object
            return types.SimpleNamespace(data=[{"session_id": payload.get("session_id") if (payload := self.upsert_payload) else None}])

    class FakeClientUpsert:
        def __init__(self, table_obj):
            self._table = table_obj

        def table(self, name):
            return self._table

    fake_table = FakeTableUpsert()
    fake_client = FakeClientUpsert(fake_table)

    import app.state_manager as sm
    monkeypatch.setattr(sm, "_supabase_client", lambda: fake_client)

    raw = {"interests": '{"a":2, "b":[4]}' }
    session_id = "test-upsert-1"

    save_state(session_id, raw)

    assert fake_table.upsert_called is True
    assert isinstance(fake_table.upsert_payload, dict)
    assert fake_table.upsert_payload["session_id"] == session_id
    assert isinstance(fake_table.upsert_payload["state"], dict)
    assert fake_table.upsert_payload["state"]["interests"]["a"] == 2
