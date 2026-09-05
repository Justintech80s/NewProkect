from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict

from .local_cache import RocksLocalCache


class RocksDBRuntime:
    """Validates that a host is ready to use RocksDB as a persistent local cache."""

    def __init__(self, namespace: str = "runtime-preflight"):
        self.cache = RocksLocalCache(namespace)
        self.root = Path(
            os.getenv("JUST_MAKER_ROCKSDB_PATH", "/tmp/just-maker-rocksdb")
        )
        self.min_free_bytes = int(
            os.getenv("JUST_MAKER_ROCKSDB_MIN_FREE_BYTES", str(2 * 1024**3))
        )

    def preflight(self) -> Dict[str, Any]:
        path = self.root
        result: Dict[str, Any] = {
            "enabled": self.cache.enabled,
            "available": self.cache.available,
            "path": str(path),
            "persistent_path_recommended": not str(path).startswith("/tmp/"),
            "writable": False,
            "read_write_test": False,
            "free_bytes": None,
            "min_free_bytes": self.min_free_bytes,
            "enough_free_space": None,
            "ready": False,
        }

        if not self.cache.enabled:
            result["reason"] = "rocksdb_disabled"
            return result

        if not self.cache.available:
            result["reason"] = "rocksdict_unavailable"
            return result

        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".just-maker-write-test"
            probe.write_text("ok")
            probe.unlink(missing_ok=True)
            result["writable"] = True
        except Exception as exc:
            result["reason"] = exc.__class__.__name__
            return result

        try:
            usage = shutil.disk_usage(path)
            result["free_bytes"] = int(usage.free)
            result["enough_free_space"] = usage.free >= self.min_free_bytes
        except Exception:
            result["enough_free_space"] = False

        probe_key = f"preflight:{time.time_ns()}"
        probe_value = {"ok": True, "timestamp_ns": time.time_ns()}
        wrote = self.cache.set(probe_key, probe_value, ttl_seconds=60)
        read_back = self.cache.get(probe_key) if wrote else None
        self.cache.delete(probe_key)
        result["read_write_test"] = bool(wrote and read_back == probe_value)

        result["ready"] = bool(
            result["writable"]
            and result["read_write_test"]
            and result["enough_free_space"]
        )
        if not result["persistent_path_recommended"]:
            result["warning"] = (
                "RocksDB is using a temporary path. Use persistent local SSD/NVMe "
                "storage on production workers."
            )
        return result
