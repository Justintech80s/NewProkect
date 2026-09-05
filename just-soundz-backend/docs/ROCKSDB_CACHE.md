# Just Maker RocksDB worker-side cache

## Role

RocksDB is a local acceleration layer only.

- Supabase/Postgres remains the authoritative system of record.
- Kafka remains the event backbone.
- GPU workers remain the generation compute layer.
- RocksDB stores disposable, recomputable hot data close to the process using it.

## Current cache targets

Backend:
- Music Brain search results
- relationship-expanded retrieval results
- production profile search responses

GPU worker:
- compiled conditioning prompts
- model/worker metadata attached to generation responses

## Enable

Install the optional dependency:

`pip install -r requirements-rocksdb.txt`

Then set:

- `JUST_MAKER_ROCKSDB_ENABLED=1`
- `JUST_MAKER_ROCKSDB_PATH=/fast-local-disk/just-maker-rocksdb`
- `JUST_MAKER_ROCKSDB_TTL_SECONDS=900`

For the GPU worker, install `gpu-worker/requirements-rocksdb.txt` as well.

## Safety

Cache misses always fall through to the normal Postgres/model path.
If RocksDB is absent, disabled, corrupted or unavailable, Just Maker continues operating.

Do not store user authentication tokens, private Supabase service keys or Kafka credentials in RocksDB.

## Scaling

Each backend/GPU host keeps its own local cache. The cache is intentionally not shared between machines; Kafka and Postgres provide the distributed coordination and durable state.
