from __future__ import annotations

import os
import time

from .services.event_bus import KafkaEventBus


def main():
    bus = KafkaEventBus()
    interval = float(os.getenv("JUST_MAKER_KAFKA_RELAY_INTERVAL_SECONDS", "2"))
    batch = int(os.getenv("JUST_MAKER_KAFKA_RELAY_BATCH_SIZE", "100"))

    while True:
        result = bus.relay_pending(limit=batch)
        if not result.get("configured"):
            time.sleep(max(5.0, interval))
            continue
        time.sleep(interval)


if __name__ == "__main__":
    main()
