from __future__ import annotations

import json
import sys

from .services.rocksdb_runtime import RocksDBRuntime


def main() -> int:
    result = RocksDBRuntime().preflight()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    sys.exit(main())
