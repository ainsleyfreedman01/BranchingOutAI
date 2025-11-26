# Changelog

## Unreleased

- Add atomic `upsert` support to `backend/app/state_manager.py` with a safe
  fallback to select→update/insert for compatibility. Improves persistence
  reliability and reduces race conditions when saving session state.
- Add unit test `backend/tests/test_save_state_upsert.py` to assert `.upsert()`
  is used when available by the Supabase client.
