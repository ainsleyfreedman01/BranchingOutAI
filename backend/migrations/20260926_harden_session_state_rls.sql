BEGIN;

-- Keep session_id as the global conflict key used by the application, while
-- retaining a user-scoped lookup index for authenticated session reads.
DROP INDEX IF EXISTS public.session_states_user_id_session_id_unique_idx;
CREATE INDEX IF NOT EXISTS session_states_user_id_session_id_idx
  ON public.session_states (user_id, session_id);

-- Ensure PostgREST has a unique conflict target even if the original key was
-- not declared as a primary key or unique constraint.
DO $$
DECLARE
  session_id_att smallint;
BEGIN
  SELECT attnum INTO session_id_att
  FROM pg_attribute
  WHERE attrelid = 'public.session_states'::regclass
    AND attname = 'session_id'
    AND NOT attisdropped;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_index
    WHERE indrelid = 'public.session_states'::regclass
      AND indisunique
      AND indpred IS NULL
      AND indnkeyatts = 1
      AND indkey[0] = session_id_att
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX session_states_session_id_unique_idx ON public.session_states (session_id)';
  END IF;
END $$;

ALTER TABLE public.session_states ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS session_states_authenticated_owner ON public.session_states;
DROP POLICY IF EXISTS session_states_authenticated_owner_guard ON public.session_states;

CREATE POLICY session_states_authenticated_owner
  ON public.session_states
  AS PERMISSIVE
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Restrictive policies are ANDed with permissive policies, so an older broad
-- permissive policy cannot grant access to another user's session row.
CREATE POLICY session_states_authenticated_owner_guard
  ON public.session_states
  AS RESTRICTIVE
  FOR ALL
  TO public
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

COMMIT;