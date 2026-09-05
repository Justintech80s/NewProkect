CREATE TABLE IF NOT EXISTS public.creative_memories (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES public.generation_jobs(id) ON DELETE CASCADE,
    score DOUBLE PRECISION NOT NULL DEFAULT 0,
    recipe JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id,job_id)
);

CREATE INDEX IF NOT EXISTS creative_memories_user_score_idx
ON public.creative_memories (user_id,score DESC,updated_at DESC);

ALTER TABLE public.creative_memories ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.creative_memories FROM anon,authenticated;
GRANT SELECT ON public.creative_memories TO authenticated;
GRANT ALL ON public.creative_memories TO service_role;

CREATE POLICY just_maker_user_creative_memories_select
ON public.creative_memories
FOR SELECT TO authenticated
USING (user_id=auth.uid());

CREATE POLICY just_maker_service_creative_memories
ON public.creative_memories
FOR ALL TO service_role
USING (true) WITH CHECK (true);
