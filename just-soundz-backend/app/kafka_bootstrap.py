from __future__ import annotations

import json
import sys

from .services.kafka_runtime import KafkaRuntime


def main() -> int:
    runtime = KafkaRuntime()
    result = runtime.ensure_topics()
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result.get("configured"):
        return 2
    if result.get("failed"):
        return 1

    health = runtime.health()
    print(json.dumps(health, indent=2, sort_keys=True))
    return 0 if health.get("ready") else 1


if __name__ == "__main__":
    sys.exit(main())
