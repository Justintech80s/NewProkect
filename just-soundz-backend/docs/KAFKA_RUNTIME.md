# Just Maker Kafka runtime

Phase 45 turns the previously prepared Kafka code into a runtime-ready service
configuration. It does not claim that a broker is connected unless the health
check succeeds.

## Local Kafka

From `just-soundz-backend`:

`docker compose -f docker-compose.kafka.yml up -d`

Then configure the backend:

`JUST_MAKER_KAFKA_BOOTSTRAP_SERVERS=localhost:9092`

Bootstrap required topics:

`python -m app.kafka_bootstrap`

Required topics:

- `justmaker.jobs`
- `justmaker.gpu.requests`
- `justmaker.gpu.results`
- `justmaker.cache`
- `justmaker.dead-letter`

The local compose file uses a single Kafka KRaft broker for development/testing.
Production should use multiple brokers or a managed Kafka service with
replication greater than one.

## Managed Kafka

Set the broker endpoints and, if required:

- `JUST_MAKER_KAFKA_SECURITY_PROTOCOL=SASL_SSL`
- `JUST_MAKER_KAFKA_SASL_MECHANISM=PLAIN` or the provider's required mechanism
- `JUST_MAKER_KAFKA_SASL_USERNAME=...`
- `JUST_MAKER_KAFKA_SASL_PASSWORD=...`

Do not commit credentials.

## Processes

API:

`uvicorn app.main:app --host 0.0.0.0 --port 8000`

Postgres outbox relay:

`python -m app.event_relay`

Backend cache invalidator:

`python -m app.cache_invalidator`

GPU Kafka consumer, on GPU host:

`python kafka_consumer.py`

GPU cache invalidator, on GPU host:

`python cache_invalidator.py`

## Health

The authenticated `/v1/event-backbone` endpoint reports Kafka runtime health,
broker count, missing topics, Postgres outbox availability and configured topic
names.

A runtime is considered ready only when:

1. a Kafka broker can be reached,
2. at least one broker is visible, and
3. all required topics exist.

Supabase/Postgres remains the authoritative store.
