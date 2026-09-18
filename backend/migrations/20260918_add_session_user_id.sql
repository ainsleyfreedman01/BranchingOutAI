BEGIN;

ALTER TABLE public.session_states
  ADD COLUMN IF NOT EXISTS user_id uuid;

CREATE INDEX IF NOT EXISTS session_states_user_id_session_id_idx
  ON public.session_states (user_id, session_id);

CREATE UNIQUE INDEX IF NOT EXISTS session_states_user_id_session_id_unique_idx
  ON public.session_states (user_id, session_id)
  WHERE user_id IS NOT NULL;

UPDATE public.session_states
SET user_id = (state ->> 'user_id')::uuid
WHERE user_id IS NULL
  AND jsonb_typeof(state) = 'object'
  AND state ? 'user_id'
  AND state ->> 'user_id' ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$';

COMMIT;
