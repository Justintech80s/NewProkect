CREATE TABLE IF NOT EXISTS public.generation_evaluations (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL UNIQUE REFERENCES public.generation_jobs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT,
    overall_score DOUBLE PRECISION NOT NULL,
    grade TEXT NOT NULL,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    scores JSONB NOT NULL DEFAULT '{}',
    issues JSONB NOT NULL DEFAULT '[]',
    routing JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS generation_evaluations_provider_idx
ON public.generation_evaluations (provider, overall_score DESC);

CREATE INDEX IF NOT EXISTS generation_evaluations_user_idx
ON public.generation_evaluations (user_id, created_at DESC);

ALTER TABLE public.generation_evaluations ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.generation_evaluations FROM anon, authenticated;
GRANT SELECT ON public.generation_evaluations TO authenticated;
GRANT ALL ON public.generation_evaluations TO service_role;

CREATE POLICY just_maker_user_generation_evaluations_select
ON public.generation_evaluations
FOR SELECT TO authenticated
USING (user_id = auth.uid());

CREATE POLICY just_maker_service_generation_evaluations
ON public.generation_evaluations
FOR ALL TO service_role
USING (true) WITH CHECK (true);
