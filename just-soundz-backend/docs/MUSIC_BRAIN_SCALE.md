# Phase 48 — Music Brain dataset scale

Just Maker's Music Brain can ingest large metadata catalogs in resumable batches
while keeping copyrighted audio separate from metadata knowledge.

Pipeline:

source adapter -> manifest/rights defaults -> quality gate -> deterministic
fingerprint -> normalized record -> Postgres/pgvector -> relationship graph ->
production profile -> Kafka cache invalidation.

## Important rights boundary

Large metadata catalogs expand what Just Maker knows about artists, recordings,
eras, genres, credits and production relationships. Metadata ingestion does not
grant permission to copy or sample the corresponding recordings.

Metadata-only manifests default to:

- rights status: reference_only
- sampling_allowed: false
- commercial_use: false

Audio becomes eligible for automatic sampling only through the existing cleared
sample-asset/rights pipeline.

## Scale controls

Batch ingestion supports configurable checkpoint intervals, duplicate detection,
quality rejection counters, resumable job IDs, and a configurable maximum error
sample. The deterministic fingerprint prevents repeated records inside the same
batch from wasting embedding/graph work.

For truly large imports, feed source records as iterators/streams rather than
materializing the full catalog in memory.
