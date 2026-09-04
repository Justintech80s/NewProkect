CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS songs (
    id BIGSERIAL PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    artist_name TEXT NOT NULL,
    album_name TEXT,
    release_year INTEGER,
    bpm DOUBLE PRECISION,
    musical_key TEXT,
    genres TEXT[] NOT NULL DEFAULT '{}',
    mood TEXT[] NOT NULL DEFAULT '{}',
    instruments TEXT[] NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS songs_artist_idx ON songs (artist_name);
CREATE INDEX IF NOT EXISTS songs_year_idx ON songs (release_year);
CREATE INDEX IF NOT EXISTS songs_bpm_idx ON songs (bpm);
CREATE INDEX IF NOT EXISTS songs_genres_gin_idx ON songs USING GIN (genres);

CREATE TABLE IF NOT EXISTS song_rights (
    song_id BIGINT PRIMARY KEY REFERENCES songs(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'unknown',
    source TEXT,
    license_name TEXT,
    commercial_use BOOLEAN NOT NULL DEFAULT FALSE,
    sampling_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS song_embeddings (
    song_id BIGINT PRIMARY KEY REFERENCES songs(id) ON DELETE CASCADE,
    embedding VECTOR(512) NOT NULL
);

CREATE INDEX IF NOT EXISTS song_embeddings_hnsw_cosine_idx
ON song_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS audio_fingerprints (
    id BIGSERIAL PRIMARY KEY,
    song_id BIGINT REFERENCES songs(id) ON DELETE SET NULL,
    algorithm TEXT NOT NULL,
    fingerprint TEXT UNIQUE NOT NULL,
    source_uri TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sample_assets (
    id BIGSERIAL PRIMARY KEY,
    song_id BIGINT REFERENCES songs(id) ON DELETE SET NULL,
    source_uri TEXT NOT NULL,
    storage_uri TEXT,
    rights_status TEXT NOT NULL DEFAULT 'unknown',
    sampling_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    commercial_use BOOLEAN NOT NULL DEFAULT FALSE,
    duration_seconds DOUBLE PRECISION,
    bpm DOUBLE PRECISION,
    musical_key TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS sample_assets_eligibility_idx
ON sample_assets (sampling_allowed, commercial_use);
