from __future__ import annotations

import json
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List


class EventOutbox:
    """Durable Postgres outbox used before Kafka publication."""

    def __init__(self):
        self.database_url = os.getenv("JUST_MAKER_DATABASE_URL")

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    def enqueue(
        self,
        topic: str,
        event_type: str,
        payload: Dict[str, Any],
        *,
        key: str | None = None,
        event_id: str | None = None,
    ) -> Dict[str, Any]:
        event_id = event_id or str(uuid.uuid4())
        envelope = {
            "event_id": event_id,
            "event_type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "source": "just-maker-backend",
            "payload": payload,
        }

        if not self.configured:
            return {
                "stored": False,
                "event_id": event_id,
                "topic": topic,
                "key": key,
                "envelope": envelope,
            }

        import psycopg

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO event_outbox(
                        event_id,topic,event_key,event_type,payload,status
                    )
                    VALUES (%s::uuid,%s,%s,%s,%s::jsonb,'pending')
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (
                        event_id,
                        topic,
                        key,
                        event_type,
                        json.dumps(envelope),
                    ),
                )
                conn.commit()

        return {
            "stored": True,
            "event_id": event_id,
            "topic": topic,
            "key": key,
            "envelope": envelope,
        }

    def pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.configured:
            return []

        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT event_id::text,topic,event_key,event_type,payload,attempts
                    FROM event_outbox
                    WHERE status='pending'
                       OR (
                            status='failed'
                            AND next_attempt_at IS NOT NULL
                            AND next_attempt_at <= NOW()
                       )
                    ORDER BY created_at
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                    """,
                    (max(1, min(int(limit), 1000)),),
                )
                rows = cur.fetchall()

        return [{
            "event_id": r[0],
            "topic": r[1],
            "key": r[2],
            "event_type": r[3],
            "payload": r[4],
            "attempts": int(r[5] or 0),
        } for r in rows]

    def mark_published(self, event_id: str) -> None:
        if not self.configured:
            return
        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE event_outbox
                    SET status='published',
                        published_at=NOW(),
                        last_error=NULL
                    WHERE event_id=%s::uuid
                    """,
                    (event_id,),
                )
                conn.commit()

    def mark_failed(self, event_id: str, error: str) -> None:
        if not self.configured:
            return
        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE event_outbox
                    SET status='failed',
                        attempts=attempts+1,
                        last_error=%s,
                        next_attempt_at=NOW() + (
                            LEAST(300, POWER(2, LEAST(attempts+1,8)))::text
                            || ' seconds'
                        )::interval
                    WHERE event_id=%s::uuid
                    """,
                    (error[:1000], event_id),
                )
                conn.commit()


class KafkaEventBus:
    """Kafka producer with Postgres outbox durability and graceful fallback."""

    def __init__(self, outbox: EventOutbox | None = None):
        self.outbox = outbox or EventOutbox()
        self.bootstrap_servers = os.getenv("JUST_MAKER_KAFKA_BOOTSTRAP_SERVERS")
        self.client_id = os.getenv(
            "JUST_MAKER_KAFKA_CLIENT_ID",
            f"just-maker-{socket.gethostname()}",
        )
        self.security_protocol = os.getenv(
            "JUST_MAKER_KAFKA_SECURITY_PROTOCOL",
            "PLAINTEXT",
        )
        self.sasl_mechanism = os.getenv("JUST_MAKER_KAFKA_SASL_MECHANISM")
        self.sasl_username = os.getenv("JUST_MAKER_KAFKA_SASL_USERNAME")
        self.sasl_password = os.getenv("JUST_MAKER_KAFKA_SASL_PASSWORD")
        self._producer = None

    @property
    def configured(self) -> bool:
        return bool(self.bootstrap_servers)

    def emit(
        self,
        topic: str,
        event_type: str,
        payload: Dict[str, Any],
        *,
        key: str | None = None,
    ) -> Dict[str, Any]:
        queued = self.outbox.enqueue(
            topic,
            event_type,
            payload,
            key=key,
        )

        if not self.configured:
            return {
                **queued,
                "published": False,
                "reason": "kafka_not_configured",
            }

        try:
            self._publish(
                topic=topic,
                key=key,
                envelope=queued["envelope"],
            )
            if queued.get("stored"):
                self.outbox.mark_published(queued["event_id"])
            return {
                **queued,
                "published": True,
            }
        except Exception as exc:
            if queued.get("stored"):
                self.outbox.mark_failed(queued["event_id"], str(exc))
            return {
                **queued,
                "published": False,
                "reason": exc.__class__.__name__,
            }

    def relay_pending(self, limit: int = 100) -> Dict[str, Any]:
        if not self.configured:
            return {
                "configured": False,
                "published": 0,
                "failed": 0,
            }

        published = 0
        failed = 0
        for event in self.outbox.pending(limit=limit):
            try:
                self._publish(
                    topic=event["topic"],
                    key=event.get("key"),
                    envelope=event["payload"],
                )
                self.outbox.mark_published(event["event_id"])
                published += 1
            except Exception as exc:
                self.outbox.mark_failed(event["event_id"], str(exc))
                failed += 1

        return {
            "configured": True,
            "published": published,
            "failed": failed,
        }

    def _publish(
        self,
        *,
        topic: str,
        key: str | None,
        envelope: Dict[str, Any],
    ) -> None:
        producer = self._get_producer()
        delivery_error = []

        def delivered(err, msg):
            if err is not None:
                delivery_error.append(str(err))

        producer.produce(
            topic,
            key=key.encode("utf-8") if key else None,
            value=json.dumps(envelope).encode("utf-8"),
            on_delivery=delivered,
        )
        producer.flush(10.0)

        if delivery_error:
            raise RuntimeError(delivery_error[0])

    def _get_producer(self):
        if self._producer is not None:
            return self._producer

        from confluent_kafka import Producer

        config: Dict[str, Any] = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": self.client_id,
            "enable.idempotence": True,
            "acks": "all",
            "compression.type": "zstd",
        }

        if self.security_protocol:
            config["security.protocol"] = self.security_protocol
        if self.sasl_mechanism:
            config["sasl.mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            config["sasl.username"] = self.sasl_username
        if self.sasl_password:
            config["sasl.password"] = self.sasl_password

        self._producer = Producer(config)
        return self._producer
