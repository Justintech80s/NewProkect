CREATE TABLE IF NOT EXISTS public.operational_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    request_id TEXT,
    job_id UUID REFERENCES public.generation_jobs(id) ON DELETE SET NULL,
    provider TEXT,
    latency_ms DOUBLE PRECISION,
    success BOOLEAN,
    estimated_cost_usd DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS operational_events_time_idx
ON public.operational_events (created_at DESC);

CREATE INDEX IF NOT EXISTS operational_events_provider_idx
ON public.operational_events (provider, created_at DESC);

CREATE INDEX IF NOT EXISTS operational_events_job_idx
ON public.operational_events (job_id);

ALTER TABLE public.operational_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.operational_events FROM anon, authenticated;
GRANT ALL ON public.operational_events TO service_role;

CREATE POLICY just_maker_service_operational_events
ON public.operational_events
FOR ALL TO service_role
USING (true) WITH CHECK (true);
