# Just Maker event-driven backend

## Architecture

Supabase/Postgres remains the system of record for users, jobs, artifacts,
evaluations, preferences, Music Brain data and the durable event outbox.

Kafka is the event backbone. The backend writes lifecycle events into the
Postgres outbox before attempting Kafka publication. If Kafka is temporarily
unavailable, the outbox relay retries delivery with exponential backoff.

GPU workers can run in their existing HTTP mode or subscribe to
`justmaker.gpu.requests` using `gpu-worker/kafka_consumer.py`.

Default topics:

- `justmaker.jobs` — queued, started, completed and failed job lifecycle events
- `justmaker.gpu.requests` — future asynchronous GPU generation requests
- `justmaker.gpu.results` — GPU completion/failure events

## Processes

Backend API:

`uvicorn app.main:app --host 0.0.0.0 --port 8000`

Outbox relay:

`python -m app.event_relay`

GPU worker HTTP service:

`uvicorn app:app --host 0.0.0.0 --port 8080`

GPU worker Kafka consumer:

`python kafka_consumer.py`

## Reliability

The outbox prevents a job-state update and its event from being silently
separated when Kafka is temporarily unavailable. Kafka publishing uses
idempotent producers with `acks=all`. GPU consumers use manual offset commits.

Kafka is optional. If no broker is configured, Just Maker continues using its
existing backend/GPU routing path and stores outbox events when Postgres is
available.

## RocksDB

RocksDB is intentionally not enabled in this phase. It is reserved for a later
worker-side cache for hot Music Brain retrievals, embeddings, model metadata and
reused conditioning data. It should not replace Postgres or Kafka.
