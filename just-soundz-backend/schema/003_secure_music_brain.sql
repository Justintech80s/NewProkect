ALTER TABLE public.songs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.song_rights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.song_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audio_fingerprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sample_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dataset_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.record_provenance ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.songs FROM anon, authenticated;
REVOKE ALL ON public.song_rights FROM anon, authenticated;
REVOKE ALL ON public.song_embeddings FROM anon, authenticated;
REVOKE ALL ON public.audio_fingerprints FROM anon, authenticated;
REVOKE ALL ON public.sample_assets FROM anon, authenticated;
REVOKE ALL ON public.dataset_sources FROM anon, authenticated;
REVOKE ALL ON public.ingestion_jobs FROM anon, authenticated;
REVOKE ALL ON public.record_provenance FROM anon, authenticated;

GRANT ALL ON public.songs TO service_role;
GRANT ALL ON public.song_rights TO service_role;
GRANT ALL ON public.song_embeddings TO service_role;
GRANT ALL ON public.audio_fingerprints TO service_role;
GRANT ALL ON public.sample_assets TO service_role;
GRANT ALL ON public.dataset_sources TO service_role;
GRANT ALL ON public.ingestion_jobs TO service_role;
GRANT ALL ON public.record_provenance TO service_role;

CREATE POLICY just_maker_service_songs ON public.songs
FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY just_maker_service_song_rights ON public.song_rights
FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY just_maker_service_song_embeddings ON public.song_embeddings
FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY just_maker_service_audio_fingerprints ON public.audio_fingerprints
FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY just_maker_service_sample_assets ON public.sample_assets
FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY just_maker_service_dataset_sources ON public.dataset_sources
FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY just_maker_service_ingestion_jobs ON public.ingestion_jobs
FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY just_maker_service_record_provenance ON public.record_provenance
FOR ALL TO service_role USING (true) WITH CHECK (true);
