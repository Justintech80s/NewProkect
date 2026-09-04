# Just Maker Music Brain

This is a backend-only knowledge and sample-discovery layer. It does not change the existing website UI.

## Core components

- PostgreSQL + pgvector for large song/artist metadata and semantic similarity search.
- Neo4j adapter for artist/song/producer/genre relationship expansion.
- 512-dimensional embedding contract with a remote CLAP-compatible adapter point.
- Rights-aware sample eligibility checks.
- Audio fingerprint contract for deduplication.
- Metadata ingestion pipeline.
- API endpoints for status, search, ingestion and rights checks.

## Data model

The PostgreSQL schema stores songs, rights, embeddings, fingerprints and sample assets. The graph layer connects artists, songs, producers and genres.

## Large dataset ingestion

Use POST /v1/music-brain/ingest for normalized records. For very large imports, call the same ingestion pipeline from batch workers or queue consumers rather than sending millions of records through one web request.

Run schema/001_music_brain.sql against PostgreSQL with the pgvector extension enabled before turning on persistent semantic search.
