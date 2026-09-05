from __future__ import annotations

import json
import os
import signal
import socket
from typing import Any, Dict

from confluent_kafka import Consumer, Producer

from worker import GPUWorker


RUNNING = True


def _stop(*_args):
    global RUNNING
    RUNNING = False


def _producer_config() -> Dict[str, Any]:
    config: Dict[str, Any] = {
        "bootstrap.servers": os.environ["JUST_MAKER_KAFKA_BOOTSTRAP_SERVERS"],
        "client.id": os.getenv(
            "JUST_MAKER_KAFKA_GPU_CLIENT_ID",
            f"just-maker-gpu-{socket.gethostname()}",
        ),
        "enable.idempotence": True,
        "acks": "all",
        "compression.type": "zstd",
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


def _consumer_config() -> Dict[str, Any]:
    config = _producer_config()
    config.pop("enable.idempotence", None)
    config.pop("acks", None)
    config.pop("compression.type", None)
    config["group.id"] = os.getenv(
        "JUST_MAKER_KAFKA_GPU_GROUP_ID",
        "just-maker-gpu-workers",
    )
    config["auto.offset.reset"] = "earliest"
    config["enable.auto.commit"] = False
    return config


def _publish(producer: Producer, topic: str, key: str, payload: Dict[str, Any]):
    producer.produce(
        topic,
        key=key.encode("utf-8"),
        value=json.dumps(payload).encode("utf-8"),
    )
    producer.flush(10.0)


def main():
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    request_topic = os.getenv(
        "JUST_MAKER_KAFKA_GPU_REQUEST_TOPIC",
        "justmaker.gpu.requests",
    )
    result_topic = os.getenv(
        "JUST_MAKER_KAFKA_GPU_RESULT_TOPIC",
        "justmaker.gpu.results",
    )

    consumer = Consumer(_consumer_config())
    producer = Producer(_producer_config())
    worker = GPUWorker()
    consumer.subscribe([request_topic])

    try:
        while RUNNING:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                continue

            try:
                envelope = json.loads(msg.value().decode("utf-8"))
                payload = envelope.get("payload") or envelope
                correlation_id = str(
                    payload.get("correlation_id")
                    or envelope.get("event_id")
                    or msg.key().decode("utf-8")
                )

                result = worker.generate(
                    plan=payload.get("plan") or {},
                    conditioning=payload.get("conditioning") or {},
                    variation=int(payload.get("variation") or 0),
                )

                _publish(
                    producer,
                    result_topic,
                    correlation_id,
                    {
                        "event_type": "gpu.generation.completed",
                        "correlation_id": correlation_id,
                        "worker": socket.gethostname(),
                        "artifact_filename": result.get("artifact_filename"),
                        "provider": result.get("provider"),
                        "metadata": result.get("metadata") or {},
                    },
                )
                consumer.commit(message=msg, asynchronous=False)
            except Exception as exc:
                correlation_id = (
                    msg.key().decode("utf-8")
                    if msg.key()
                    else "unknown"
                )
                _publish(
                    producer,
                    result_topic,
                    correlation_id,
                    {
                        "event_type": "gpu.generation.failed",
                        "correlation_id": correlation_id,
                        "worker": socket.gethostname(),
                        "error_type": exc.__class__.__name__,
                        "error": str(exc)[:1000],
                    },
                )
                # Commit poison messages after reporting failure so they do not
                # loop forever. Application-level retry can publish a fresh event.
                consumer.commit(message=msg, asynchronous=False)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
