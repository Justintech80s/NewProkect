CREATE TABLE IF NOT EXISTS public.generation_feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES public.generation_jobs(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    action TEXT NOT NULL CHECK (action IN ('like','dislike','save','reject')),
    notes TEXT,
    learned_traits JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id,job_id)
);

CREATE TABLE IF NOT EXISTS public.user_music_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    traits JSONB NOT NULL DEFAULT '{}',
    feedback_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS generation_feedback_user_idx
ON public.generation_feedback (user_id,updated_at DESC);

ALTER TABLE public.generation_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_music_preferences ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.generation_feedback FROM anon,authenticated;
REVOKE ALL ON public.user_music_preferences FROM anon,authenticated;

GRANT SELECT ON public.generation_feedback TO authenticated;
GRANT SELECT ON public.user_music_preferences TO authenticated;
GRANT ALL ON public.generation_feedback TO service_role;
GRANT ALL ON public.user_music_preferences TO service_role;

CREATE POLICY just_maker_user_generation_feedback_select
ON public.generation_feedback
FOR SELECT TO authenticated
USING (user_id=auth.uid());

CREATE POLICY just_maker_user_music_preferences_select
ON public.user_music_preferences
FOR SELECT TO authenticated
USING (user_id=auth.uid());

CREATE POLICY just_maker_service_generation_feedback
ON public.generation_feedback
FOR ALL TO service_role
USING (true) WITH CHECK (true);

CREATE POLICY just_maker_service_user_music_preferences
ON public.user_music_preferences
FOR ALL TO service_role
USING (true) WITH CHECK (true);
