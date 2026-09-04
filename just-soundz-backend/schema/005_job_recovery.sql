ALTER TABLE public.generation_jobs
ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3,
ADD COLUMN IF NOT EXISTS retry_of UUID REFERENCES public.generation_jobs(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS generation_jobs_retry_idx
ON public.generation_jobs (status, retry_count, updated_at);

CREATE INDEX IF NOT EXISTS generation_jobs_retry_of_idx
ON public.generation_jobs (retry_of);
