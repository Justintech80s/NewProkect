from __future__ import annotations

import json
import os
import signal
import socket

from confluent_kafka import Consumer

from .services.local_cache import RocksLocalCache


RUNNING = True


def _stop(*_args):
    global RUNNING
    RUNNING = False


def _consumer_config():
    config = {
        "bootstrap.servers": os.environ["JUST_MAKER_KAFKA_BOOTSTRAP_SERVERS"],
        "group.id": os.getenv(
            "JUST_MAKER_KAFKA_CACHE_GROUP_ID",
            f"just-maker-cache-{socket.gethostname()}",
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
    consumer = Consumer(_consumer_config())
    consumer.subscribe([topic])

    caches = {
        "music-brain-search": RocksLocalCache("music-brain-search"),
    }

    try:
        while RUNNING:
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            try:
                envelope = json.loads(msg.value().decode("utf-8"))
                if envelope.get("event_type") != "cache.invalidate":
                    consumer.commit(message=msg, asynchronous=False)
                    continue

                payload = envelope.get("payload") or {}
                namespaces = payload.get("namespaces") or []
                for namespace in namespaces:
                    cache = caches.get(namespace)
                    if cache:
                        cache.clear()

                consumer.commit(message=msg, asynchronous=False)
            except Exception:
                # Leave the offset uncommitted so transient local errors retry.
                continue
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
