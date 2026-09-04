ALTER TABLE public.generation_jobs
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS generation_jobs_user_idx
ON public.generation_jobs (user_id, created_at DESC);

ALTER TABLE public.generation_artifacts
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS generation_artifacts_user_idx
ON public.generation_artifacts (user_id, created_at DESC);

UPDATE public.generation_artifacts a
SET user_id = j.user_id
FROM public.generation_jobs j
WHERE a.job_id = j.id
  AND a.user_id IS NULL
  AND j.user_id IS NOT NULL;

DROP POLICY IF EXISTS just_maker_user_generation_jobs_select
ON public.generation_jobs;

CREATE POLICY just_maker_user_generation_jobs_select
ON public.generation_jobs
FOR SELECT TO authenticated
USING (user_id = auth.uid());

DROP POLICY IF EXISTS just_maker_user_generation_artifacts_select
ON public.generation_artifacts;

CREATE POLICY just_maker_user_generation_artifacts_select
ON public.generation_artifacts
FOR SELECT TO authenticated
USING (user_id = auth.uid());

GRANT SELECT ON public.generation_jobs TO authenticated;
GRANT SELECT ON public.generation_artifacts TO authenticated;
