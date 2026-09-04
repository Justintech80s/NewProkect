CREATE TABLE IF NOT EXISTS generation_jobs (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'queued',
    stage TEXT NOT NULL DEFAULT 'queued',
    progress DOUBLE PRECISION NOT NULL DEFAULT 0.0
        CHECK (progress >= 0.0 AND progress <= 1.0),
    request_payload JSONB NOT NULL DEFAULT '{}',
    result_payload JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS generation_jobs_status_idx
ON generation_jobs (status, created_at DESC);

CREATE TABLE IF NOT EXISTS generation_artifacts (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    sha256 TEXT,
    bucket TEXT,
    object_path TEXT,
    storage_uri TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS generation_artifacts_job_idx
ON generation_artifacts (job_id, created_at);

ALTER TABLE public.generation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generation_artifacts ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.generation_jobs FROM anon, authenticated;
REVOKE ALL ON public.generation_artifacts FROM anon, authenticated;

GRANT ALL ON public.generation_jobs TO service_role;
GRANT ALL ON public.generation_artifacts TO service_role;

CREATE POLICY just_maker_service_generation_jobs
ON public.generation_jobs
FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY just_maker_service_generation_artifacts
ON public.generation_artifacts
FOR ALL TO service_role USING (true) WITH CHECK (true);

INSERT INTO storage.buckets (id, name, public)
VALUES ('just-maker-artifacts','just-maker-artifacts',FALSE)
ON CONFLICT (id) DO UPDATE SET public=FALSE;
