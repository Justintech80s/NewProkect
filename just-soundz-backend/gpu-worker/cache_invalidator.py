from __future__ import annotations

import json
import os
import signal
import socket

from confluent_kafka import Consumer

from local_cache import RocksLocalCache


RUNNING = True


def _stop(*_args):
    global RUNNING
    RUNNING = False


def _config():
    config = {
        "bootstrap.servers": os.environ["JUST_MAKER_KAFKA_BOOTSTRAP_SERVERS"],
        "group.id": os.getenv(
            "JUST_MAKER_KAFKA_GPU_CACHE_GROUP_ID",
            f"just-maker-gpu-cache-{socket.gethostname()}",
        ),
        "auto.offset.reset": "latest",
        "enable.auto.commit": False,
    }
    protocol = os.getenv("JUST_MAKER_KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
    if protocol:
        config["security.protocol"] = protocol
    mechanism = os.getenv("JUST_MAKER_KAFKA_SASL_MECHANISM")
    username = os.getenv("JUST_MAKER_KAFKA_SASL_USERNAME")
    password = os.getenv("JUST_MAKER_KAFKA_SASL_PASSWORD")
    if mechanism:
        config["sasl.mechanism"] = mechanism
    if username:
        config["sasl.username"] = username
    if password:
        config["sasl.password"] = password
    return config


def main():
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    topic = os.getenv("JUST_MAKER_KAFKA_CACHE_TOPIC", "justmaker.cache")
    consumer = Consumer(_config())
    consumer.subscribe([topic])
    cache = RocksLocalCache("gpu-worker")

    try:
        while RUNNING:
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            try:
                envelope = json.loads(msg.value().decode("utf-8"))
                payload = envelope.get("payload") or {}
                namespaces = payload.get("namespaces") or []
                if (
                    envelope.get("event_type") == "cache.invalidate"
                    and "gpu-worker" in namespaces
                ):
                    cache.clear()
                consumer.commit(message=msg, asynchronous=False)
            except Exception:
                continue
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
