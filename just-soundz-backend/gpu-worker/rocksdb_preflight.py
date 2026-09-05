from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

from local_cache import RocksLocalCache


def main() -> int:
    cache = RocksLocalCache("gpu-runtime-preflight")
    root = Path(os.getenv("JUST_MAKER_ROCKSDB_PATH", "/tmp/just-maker-rocksdb"))
    min_free = int(os.getenv("JUST_MAKER_ROCKSDB_MIN_FREE_BYTES", str(2 * 1024**3)))

    result = {
        "enabled": cache.enabled,
        "available": cache.available,
        "path": str(root),
        "persistent_path_recommended": not str(root).startswith("/tmp/"),
        "writable": False,
        "read_write_test": False,
        "free_bytes": None,
        "min_free_bytes": min_free,
        "enough_free_space": None,
        "ready": False,
    }

    if not cache.enabled or not cache.available:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".just-maker-gpu-write-test"
        probe.write_text("ok")
        probe.unlink(missing_ok=True)
        result["writable"] = True

        usage = shutil.disk_usage(root)
        result["free_bytes"] = int(usage.free)
        result["enough_free_space"] = usage.free >= min_free

        key = f"gpu-preflight:{time.time_ns()}"
        value = {"ok": True}
        wrote = cache.set(key, value, ttl_seconds=60)
        read_back = cache.get(key) if wrote else None
        cache.delete(key)
        result["read_write_test"] = bool(wrote and read_back == value)
        result["ready"] = bool(
            result["writable"]
            and result["read_write_test"]
            and result["enough_free_space"]
        )
    except Exception as exc:
        result["reason"] = exc.__class__.__name__

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    sys.exit(main())
