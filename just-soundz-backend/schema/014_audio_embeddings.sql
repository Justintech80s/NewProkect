CREATE TABLE IF NOT EXISTS public.sample_audio_embeddings (
    sample_asset_id BIGINT PRIMARY KEY
        REFERENCES public.sample_assets(id) ON DELETE CASCADE,
    embedding extensions.vector(512) NOT NULL,
    production_traits JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS sample_audio_embeddings_hnsw_idx
ON public.sample_audio_embeddings
USING hnsw (embedding extensions.vector_cosine_ops);

ALTER TABLE public.sample_audio_embeddings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.sample_audio_embeddings FROM anon,authenticated;
GRANT ALL ON public.sample_audio_embeddings TO service_role;

CREATE POLICY just_maker_service_sample_audio_embeddings
ON public.sample_audio_embeddings
FOR ALL TO service_role
USING (true) WITH CHECK (true);
