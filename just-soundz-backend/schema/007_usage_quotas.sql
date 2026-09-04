CREATE TABLE IF NOT EXISTS public.user_usage_limits (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    daily_job_limit INTEGER NOT NULL DEFAULT 20 CHECK (daily_job_limit > 0),
    monthly_seconds_limit INTEGER NOT NULL DEFAULT 7200 CHECK (monthly_seconds_limit > 0),
    concurrent_job_limit INTEGER NOT NULL DEFAULT 2 CHECK (concurrent_job_limit > 0),
    is_suspended BOOLEAN NOT NULL DEFAULT FALSE,
    suspension_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.usage_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES public.generation_jobs(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS usage_events_user_time_idx
ON public.usage_events (user_id, created_at DESC);

ALTER TABLE public.user_usage_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.user_usage_limits FROM anon, authenticated;
REVOKE ALL ON public.usage_events FROM anon, authenticated;

GRANT SELECT ON public.user_usage_limits TO authenticated;
GRANT SELECT ON public.usage_events TO authenticated;
GRANT ALL ON public.user_usage_limits TO service_role;
GRANT ALL ON public.usage_events TO service_role;

DROP POLICY IF EXISTS just_maker_user_usage_limits_select
ON public.user_usage_limits;
CREATE POLICY just_maker_user_usage_limits_select
ON public.user_usage_limits
FOR SELECT TO authenticated
USING (user_id = auth.uid());

DROP POLICY IF EXISTS just_maker_user_usage_events_select
ON public.usage_events;
CREATE POLICY just_maker_user_usage_events_select
ON public.usage_events
FOR SELECT TO authenticated
USING (user_id = auth.uid());

DROP POLICY IF EXISTS just_maker_service_usage_limits
ON public.user_usage_limits;
CREATE POLICY just_maker_service_usage_limits
ON public.user_usage_limits
FOR ALL TO service_role
USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS just_maker_service_usage_events
ON public.usage_events;
CREATE POLICY just_maker_service_usage_events
ON public.usage_events
FOR ALL TO service_role
USING (true) WITH CHECK (true);
