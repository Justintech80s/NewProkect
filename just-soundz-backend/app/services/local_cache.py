from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict


class RocksLocalCache:
    """Optional worker-local RocksDB cache with TTL-aware JSON values.

    Postgres remains authoritative. If RocksDB is disabled or unavailable,
    callers transparently fall back to normal computation/storage paths.
    """

    def __init__(self, namespace: str = "default"):
        self.enabled = os.getenv("JUST_MAKER_ROCKSDB_ENABLED", "0").lower() in {
            "1", "true", "yes", "on"
        }
        self.root = Path(
            os.getenv("JUST_MAKER_ROCKSDB_PATH", "/tmp/just-maker-rocksdb")
        )
        self.namespace = namespace
        self.default_ttl = int(os.getenv("JUST_MAKER_ROCKSDB_TTL_SECONDS", "900"))
        self._db = None
        self._available = None
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "deletes": 0,
            "invalidated": 0,
            "errors": 0,
        }

    @property
    def available(self) -> bool:
        if not self.enabled:
            return False
        if self._available is not None:
            return self._available
        try:
            from rocksdict import Rdict  # noqa: F401
            self._available = True
        except Exception:
            self._available = False
        return self._available

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "available": self.available,
            "namespace": self.namespace,
            "path": str(self.root / self.namespace),
            "default_ttl_seconds": self.default_ttl,
            "authoritative_store": "supabase-postgres",
            "metrics": self.metrics(),
        }

    def get(self, key: str) -> Any | None:
        if not self.available:
            self._metrics["misses"] += 1
            return None

        try:
            db = self._get_db()
            raw = db.get(self._key(key))
        except Exception:
            self._metrics["errors"] += 1
            self._metrics["misses"] += 1
            return None
        if raw is None:
            self._metrics["misses"] += 1
            return None

        try:
            record = json.loads(raw)
        except Exception:
            self.delete(key)
            return None

        expires_at = record.get("expires_at")
        if expires_at is not None and float(expires_at) <= time.time():
            self.delete(key)
            self._metrics["misses"] += 1
            return None

        self._metrics["hits"] += 1
        return record.get("value")

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> bool:
        if not self.available:
            return False

        ttl = self.default_ttl if ttl_seconds is None else int(ttl_seconds)
        record = {
            "value": value,
            "stored_at": time.time(),
            "expires_at": None if ttl <= 0 else time.time() + ttl,
        }
        try:
            self._get_db()[self._key(key)] = json.dumps(
                record,
                separators=(",", ":"),
                sort_keys=True,
                default=str,
            )
            self._metrics["writes"] += 1
            return True
        except Exception:
            self._metrics["errors"] += 1
            return False

    def delete(self, key: str) -> bool:
        if not self.available:
            return False
        db = self._get_db()
        hashed = self._key(key)
        if hashed in db:
            del db[hashed]
            self._metrics["deletes"] += 1
            return True
        return False

    def clear(self) -> int:
        if not self.available:
            return 0
        db = self._get_db()
        keys = [key for key in db.keys() if str(key).startswith(f"{self.namespace}:")]
        for key in keys:
            del db[key]
        self._metrics["invalidated"] += len(keys)
        return len(keys)

    def delete_prefix(self, prefix: str) -> int:
        if not self.available:
            return 0
        db = self._get_db()
        target = f"{self.namespace}:{prefix}"
        keys = [key for key in db.keys() if str(key).startswith(target)]
        for key in keys:
            del db[key]
        self._metrics["invalidated"] += len(keys)
        return len(keys)

    def metrics(self) -> Dict[str, Any]:
        hits = int(self._metrics["hits"])
        misses = int(self._metrics["misses"])
        lookups = hits + misses
        return {
            **self._metrics,
            "lookups": lookups,
            "hit_rate": round(hits / lookups, 4) if lookups else 0.0,
        }

    def make_key(self, prefix: str, payload: Any) -> str:
        encoded = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return f"{prefix}:{digest}"

    def _key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def _get_db(self):
        if self._db is not None:
            return self._db

        from rocksdict import Rdict

        path = self.root / self.namespace
        path.mkdir(parents=True, exist_ok=True)
        self._db = Rdict(str(path))
        return self._db
