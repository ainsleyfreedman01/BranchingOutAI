BEGIN;

CREATE TABLE IF NOT EXISTS public.api_rate_limits (
  rate_key text PRIMARY KEY,
  window_started_at timestamptz NOT NULL,
  request_count integer NOT NULL CHECK (request_count > 0)
);

CREATE INDEX IF NOT EXISTS api_rate_limits_window_started_at_idx
  ON public.api_rate_limits (window_started_at);

ALTER TABLE public.api_rate_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.api_rate_limits FROM PUBLIC, anon, authenticated;

CREATE OR REPLACE FUNCTION public.consume_api_rate_limit(
  p_key text,
  p_limit integer,
  p_window_seconds integer
)
RETURNS TABLE (allowed boolean, retry_after integer)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_now timestamptz := clock_timestamp();
  bucket_started_at timestamptz;
  bucket_count integer;
BEGIN
  IF p_key IS NULL OR length(p_key) <> 64
     OR p_limit < 1 OR p_limit > 100000
     OR p_window_seconds < 1 OR p_window_seconds > 86400 THEN
    RAISE EXCEPTION 'Invalid rate-limit parameters';
  END IF;

  -- Opportunistically prune old identifiers without requiring a scheduler.
  IF random() < 0.01 AND pg_try_advisory_xact_lock(72840122613001) THEN
    DELETE FROM public.api_rate_limits
    WHERE window_started_at < v_now - interval '1 day';
  END IF;

  INSERT INTO public.api_rate_limits AS existing_bucket
    (rate_key, window_started_at, request_count)
  VALUES (p_key, v_now, 1)
  ON CONFLICT (rate_key) DO UPDATE
  SET window_started_at = CASE
        WHEN existing_bucket.window_started_at <= v_now - make_interval(secs => p_window_seconds)
          THEN EXCLUDED.window_started_at
        ELSE existing_bucket.window_started_at
      END,
      request_count = CASE
        WHEN existing_bucket.window_started_at <= v_now - make_interval(secs => p_window_seconds)
          THEN 1
        ELSE LEAST(existing_bucket.request_count + 1, p_limit + 1)
      END
  RETURNING existing_bucket.window_started_at, existing_bucket.request_count
  INTO bucket_started_at, bucket_count;

  RETURN QUERY SELECT
    bucket_count <= p_limit,
    CASE
      WHEN bucket_count <= p_limit THEN 0
      ELSE GREATEST(
        1,
        CEIL(EXTRACT(EPOCH FROM (
          bucket_started_at + make_interval(secs => p_window_seconds) - v_now
        )))::integer
      )
    END;
END;
$$;

REVOKE ALL ON FUNCTION public.consume_api_rate_limit(text, integer, integer)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.consume_api_rate_limit(text, integer, integer)
  TO service_role;

COMMIT;