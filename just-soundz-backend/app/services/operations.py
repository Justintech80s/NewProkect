from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict


class OperationsMetrics:
    """Records operational events, latency, failures and estimated generation cost."""

    def __init__(self):
        self.database_url = os.getenv("JUST_MAKER_DATABASE_URL")
        self.default_cost_per_gpu_second = float(
            os.getenv("JUST_MAKER_GPU_COST_PER_SECOND", "0.0008")
        )

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    def record(
        self,
        event_type: str,
        *,
        request_id: str | None = None,
        job_id: str | None = None,
        provider: str | None = None,
        latency_ms: float | None = None,
        success: bool | None = None,
        estimated_cost_usd: float | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        if not self.configured:
            return

        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO operational_events(
                        event_type,request_id,job_id,provider,latency_ms,
                        success,estimated_cost_usd,metadata,created_at
                    )
                    VALUES (%s,%s,%s::uuid,%s,%s,%s,%s,%s::jsonb,%s::timestamptz)
                    """,
                    (
                        event_type,
                        request_id,
                        job_id,
                        provider,
                        latency_ms,
                        success,
                        estimated_cost_usd,
                        json.dumps(metadata or {}),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()

    def estimate_generation_cost(
        self,
        duration_seconds: int,
        attempts: int = 1,
        stem_count: int = 1,
    ) -> float:
        gpu_seconds = max(0, duration_seconds) * max(1, attempts) * max(1, stem_count)
        return round(gpu_seconds * self.default_cost_per_gpu_second, 6)

    def summary(self, hours: int = 24) -> Dict[str, Any]:
        if not self.configured:
            return {"configured": False, "providers": [], "events": 0}

        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT provider,
                           count(*)::int,
                           avg(latency_ms)::float,
                           avg(CASE WHEN success THEN 1.0 ELSE 0.0 END)::float,
                           sum(COALESCE(estimated_cost_usd,0))::float
                    FROM operational_events
                    WHERE created_at >= now() - (%s || ' hours')::interval
                      AND provider IS NOT NULL
                    GROUP BY provider
                    ORDER BY count(*) DESC
                    """,
                    (hours,),
                )
                rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM operational_events
                    WHERE created_at >= now() - (%s || ' hours')::interval
                    """,
                    (hours,),
                )
                total = cur.fetchone()[0]

        return {
            "configured": True,
            "window_hours": hours,
            "events": total,
            "providers": [{
                "provider": r[0],
                "events": r[1],
                "avg_latency_ms": round(float(r[2] or 0.0), 2),
                "success_rate": round(float(r[3] or 0.0), 4),
                "estimated_cost_usd": round(float(r[4] or 0.0), 4),
            } for r in rows],
        }


class Stopwatch:
    def __enter__(self):
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.elapsed_ms = (time.perf_counter() - self.started) * 1000.0
