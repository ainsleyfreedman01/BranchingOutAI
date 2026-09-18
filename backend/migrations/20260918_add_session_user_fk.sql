BEGIN;

-- Ownership constraint: a session_states row must belong to a real user, and
-- deleting a user cleans up their sessions automatically (defense in depth
-- alongside the app's explicit delete in DELETE /account).
ALTER TABLE public.session_states
  ADD CONSTRAINT session_states_user_id_fkey
  FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE;

COMMIT;
