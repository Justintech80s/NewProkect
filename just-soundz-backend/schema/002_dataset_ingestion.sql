CREATE TABLE IF NOT EXISTS dataset_sources (
    id BIGSERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    base_url TEXT,
    metadata_only BOOLEAN NOT NULL DEFAULT TRUE,
    license_name TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY,
    source_name TEXT NOT NULL,
    query TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    processed_count BIGINT NOT NULL DEFAULT 0,
    stored_count BIGINT NOT NULL DEFAULT 0,
    failed_count BIGINT NOT NULL DEFAULT 0,
    checkpoint JSONB NOT NULL DEFAULT '{}',
    error_summary JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ingestion_jobs_status_idx
ON ingestion_jobs (status, created_at DESC);

CREATE TABLE IF NOT EXISTS record_provenance (
    id BIGSERIAL PRIMARY KEY,
    song_id BIGINT REFERENCES songs(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    source_url TEXT,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    license_name TEXT,
    metadata_only BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}',
    UNIQUE (source_name, source_record_id)
);

CREATE INDEX IF NOT EXISTS record_provenance_song_idx
ON record_provenance (song_id);

INSERT INTO dataset_sources (name, base_url, metadata_only, license_name)
VALUES (
    'musicbrainz',
    'https://musicbrainz.org',
    TRUE,
    'MusicBrainz metadata terms apply'
)
ON CONFLICT (name) DO NOTHING;
