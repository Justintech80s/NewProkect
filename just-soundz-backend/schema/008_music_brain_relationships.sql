CREATE TABLE IF NOT EXISTS public.music_entities (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    external_id TEXT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (entity_type, normalized_name)
);

CREATE INDEX IF NOT EXISTS music_entities_type_name_idx
ON public.music_entities (entity_type, normalized_name);

CREATE TABLE IF NOT EXISTS public.music_relationships (
    id BIGSERIAL PRIMARY KEY,
    source_entity_id BIGINT NOT NULL REFERENCES public.music_entities(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    target_entity_id BIGINT NOT NULL REFERENCES public.music_entities(id) ON DELETE CASCADE,
    song_id BIGINT REFERENCES public.songs(id) ON DELETE CASCADE,
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    provenance JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_entity_id, relationship_type, target_entity_id, song_id)
);

CREATE INDEX IF NOT EXISTS music_relationships_source_idx
ON public.music_relationships (source_entity_id, relationship_type);
CREATE INDEX IF NOT EXISTS music_relationships_target_idx
ON public.music_relationships (target_entity_id, relationship_type);
CREATE INDEX IF NOT EXISTS music_relationships_song_idx
ON public.music_relationships (song_id);

CREATE TABLE IF NOT EXISTS public.song_credits (
    id BIGSERIAL PRIMARY KEY,
    song_id BIGINT NOT NULL REFERENCES public.songs(id) ON DELETE CASCADE,
    credit_type TEXT NOT NULL,
    person_name TEXT NOT NULL,
    external_id TEXT,
    position INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}',
    UNIQUE(song_id, credit_type, person_name)
);

CREATE INDEX IF NOT EXISTS song_credits_song_type_idx
ON public.song_credits (song_id, credit_type);

CREATE TABLE IF NOT EXISTS public.production_profiles (
    song_id BIGINT PRIMARY KEY REFERENCES public.songs(id) ON DELETE CASCADE,
    era TEXT,
    tempo_bucket TEXT,
    energy DOUBLE PRECISION,
    swing DOUBLE PRECISION,
    syncopation DOUBLE PRECISION,
    drum_density DOUBLE PRECISION,
    harmonic_complexity DOUBLE PRECISION,
    bass_prominence DOUBLE PRECISION,
    sample_chop_intensity DOUBLE PRECISION,
    texture_tags TEXT[] NOT NULL DEFAULT '{}',
    techniques TEXT[] NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.music_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.music_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.song_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.production_profiles ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.music_entities FROM anon, authenticated;
REVOKE ALL ON public.music_relationships FROM anon, authenticated;
REVOKE ALL ON public.song_credits FROM anon, authenticated;
REVOKE ALL ON public.production_profiles FROM anon, authenticated;

GRANT ALL ON public.music_entities TO service_role;
GRANT ALL ON public.music_relationships TO service_role;
GRANT ALL ON public.song_credits TO service_role;
GRANT ALL ON public.production_profiles TO service_role;

CREATE POLICY just_maker_service_music_entities
ON public.music_entities FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY just_maker_service_music_relationships
ON public.music_relationships FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY just_maker_service_song_credits
ON public.song_credits FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY just_maker_service_production_profiles
ON public.production_profiles FOR ALL TO service_role USING (true) WITH CHECK (true);
