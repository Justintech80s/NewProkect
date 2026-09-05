from __future__ import annotations

import os
import time
from typing import Any, Dict, List


class KafkaRuntime:
    """Admin/health facade for a real Kafka broker or managed Kafka cluster."""

    def __init__(self):
        self.bootstrap_servers = os.getenv("JUST_MAKER_KAFKA_BOOTSTRAP_SERVERS")
        self.client_id = os.getenv("JUST_MAKER_KAFKA_ADMIN_CLIENT_ID", "just-maker-admin")
        self.security_protocol = os.getenv(
            "JUST_MAKER_KAFKA_SECURITY_PROTOCOL",
            "PLAINTEXT",
        )
        self.sasl_mechanism = os.getenv("JUST_MAKER_KAFKA_SASL_MECHANISM")
        self.sasl_username = os.getenv("JUST_MAKER_KAFKA_SASL_USERNAME")
        self.sasl_password = os.getenv("JUST_MAKER_KAFKA_SASL_PASSWORD")
        self.default_partitions = int(
            os.getenv("JUST_MAKER_KAFKA_DEFAULT_PARTITIONS", "6")
        )
        self.replication_factor = int(
            os.getenv("JUST_MAKER_KAFKA_REPLICATION_FACTOR", "1")
        )

    @property
    def configured(self) -> bool:
        return bool(self.bootstrap_servers)

    def required_topics(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": os.getenv(
                    "JUST_MAKER_KAFKA_JOB_TOPIC",
                    "justmaker.jobs",
                ),
                "partitions": self.default_partitions,
            },
            {
                "name": os.getenv(
                    "JUST_MAKER_KAFKA_GPU_REQUEST_TOPIC",
                    "justmaker.gpu.requests",
                ),
                "partitions": self.default_partitions,
            },
            {
                "name": os.getenv(
                    "JUST_MAKER_KAFKA_GPU_RESULT_TOPIC",
                    "justmaker.gpu.results",
                ),
                "partitions": self.default_partitions,
            },
            {
                "name": os.getenv(
                    "JUST_MAKER_KAFKA_CACHE_TOPIC",
                    "justmaker.cache",
                ),
                "partitions": max(3, self.default_partitions // 2),
            },
            {
                "name": os.getenv(
                    "JUST_MAKER_KAFKA_DLQ_TOPIC",
                    "justmaker.dead-letter",
                ),
                "partitions": max(3, self.default_partitions // 2),
            },
        ]

    def health(self, timeout_seconds: float = 3.0) -> Dict[str, Any]:
        if not self.configured:
            return {
                "configured": False,
                "connected": False,
                "reason": "kafka_not_configured",
                "required_topics": self.required_topics(),
            }

        started = time.perf_counter()
        try:
            admin = self._admin()
            metadata = admin.list_topics(timeout=timeout_seconds)
            brokers = {
                str(node_id): {
                    "host": broker.host,
                    "port": broker.port,
                }
                for node_id, broker in metadata.brokers.items()
            }
            topics = sorted(metadata.topics.keys())
            required = [item["name"] for item in self.required_topics()]
            missing = [name for name in required if name not in topics]
            return {
                "configured": True,
                "connected": True,
                "latency_ms": round(
                    (time.perf_counter() - started) * 1000.0,
                    2,
                ),
                "broker_count": len(brokers),
                "brokers": brokers,
                "topics": topics,
                "required_topics": required,
                "missing_topics": missing,
                "ready": not missing and bool(brokers),
            }
        except Exception as exc:
            return {
                "configured": True,
                "connected": False,
                "reason": exc.__class__.__name__,
                "latency_ms": round(
                    (time.perf_counter() - started) * 1000.0,
                    2,
                ),
                "required_topics": self.required_topics(),
            }

    def ensure_topics(self, timeout_seconds: float = 15.0) -> Dict[str, Any]:
        if not self.configured:
            return {
                "configured": False,
                "created": [],
                "existing": [],
                "failed": {},
                "reason": "kafka_not_configured",
            }

        from confluent_kafka.admin import NewTopic

        admin = self._admin()
        metadata = admin.list_topics(timeout=min(timeout_seconds, 5.0))
        existing_names = set(metadata.topics.keys())

        specs = self.required_topics()
        existing = [item["name"] for item in specs if item["name"] in existing_names]
        missing = [item for item in specs if item["name"] not in existing_names]

        futures = admin.create_topics(
            [
                NewTopic(
                    item["name"],
                    num_partitions=int(item["partitions"]),
                    replication_factor=self.replication_factor,
                )
                for item in missing
            ],
            operation_timeout=timeout_seconds,
        ) if missing else {}

        created = []
        failed: Dict[str, str] = {}
        for topic, future in futures.items():
            try:
                future.result(timeout=timeout_seconds)
                created.append(topic)
            except Exception as exc:
                failed[topic] = str(exc)[:500]

        return {
            "configured": True,
            "created": sorted(created),
            "existing": sorted(existing),
            "failed": failed,
            "ready": not failed,
        }

    def _admin(self):
        from confluent_kafka.admin import AdminClient

        config: Dict[str, Any] = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": self.client_id,
        }
        if self.security_protocol:
            config["security.protocol"] = self.security_protocol
        if self.sasl_mechanism:
            config["sasl.mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            config["sasl.username"] = self.sasl_username
        if self.sasl_password:
            config["sasl.password"] = self.sasl_password

        return AdminClient(config)
