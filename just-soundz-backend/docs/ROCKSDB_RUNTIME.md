# Just Maker RocksDB runtime enablement

Phase 46 turns the existing optional RocksDB code into a host-ready runtime
configuration.

## Backend worker

Install:

`pip install -r requirements-rocksdb.txt`

Use a persistent local SSD/NVMe path:

`JUST_MAKER_ROCKSDB_ENABLED=1`

`JUST_MAKER_ROCKSDB_PATH=/var/lib/just-maker/rocksdb`

Run the preflight:

`PYTHONPATH=. python -m app.rocksdb_preflight`

## GPU worker

Install:

`pip install -r requirements-rocksdb.txt`

Run:

`python rocksdb_preflight.py`

The same persistent local path should be mounted into the worker process.

## What preflight verifies

- RocksDB/rocksdict is installed
- cache path can be created
- cache path is writable
- there is enough free disk space
- a real RocksDB write/read/delete round trip succeeds

## Storage guidance

Use host-local SSD or NVMe storage. Avoid network filesystems for RocksDB unless
the filesystem/vendor explicitly supports its locking and fsync behavior.

RocksDB remains disposable cache state. Supabase/Postgres remains authoritative,
and Kafka remains responsible for distributed invalidation/coherence.
