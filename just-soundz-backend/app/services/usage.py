from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict


class UsageQuotaService:
    """Tracks per-user usage and enforces generation quotas before expensive work starts."""

    def __init__(self):
        self.database_url = os.getenv("JUST_MAKER_DATABASE_URL")
        self.default_daily_jobs = int(os.getenv("JUST_MAKER_DAILY_JOB_LIMIT", "20"))
        self.default_monthly_seconds = int(os.getenv("JUST_MAKER_MONTHLY_SECONDS_LIMIT", "7200"))
        self.default_concurrent_jobs = int(os.getenv("JUST_MAKER_CONCURRENT_JOB_LIMIT", "2"))

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    def ensure_profile(self, user_id: str) -> None:
        if not self.configured:
            return
        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_usage_limits (
                        user_id,daily_job_limit,monthly_seconds_limit,concurrent_job_limit
                    )
                    VALUES (%s::uuid,%s,%s,%s)
                    ON CONFLICT (user_id) DO NOTHING
                    """,
                    (
                        user_id,
                        self.default_daily_jobs,
                        self.default_monthly_seconds,
                        self.default_concurrent_jobs,
                    ),
                )
                conn.commit()

    def status(self, user_id: str) -> Dict[str, Any]:
        self.ensure_profile(user_id)
        if not self.configured:
            return {
                "configured": False,
                "allowed": True,
                "reason": "usage_database_not_configured",
            }

        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        l.daily_job_limit,
                        l.monthly_seconds_limit,
                        l.concurrent_job_limit,
                        l.is_suspended,
                        l.suspension_reason,
                        COALESCE((
                            SELECT count(*)
                            FROM generation_jobs j
                            WHERE j.user_id=l.user_id
                              AND j.created_at >= date_trunc('day', now())
                        ),0) AS daily_jobs,
                        COALESCE((
                            SELECT sum((j.request_payload->>'duration_seconds')::int)
                            FROM generation_jobs j
                            WHERE j.user_id=l.user_id
                              AND j.status='complete'
                              AND j.created_at >= date_trunc('month', now())
                        ),0) AS monthly_seconds,
                        COALESCE((
                            SELECT count(*)
                            FROM generation_jobs j
                            WHERE j.user_id=l.user_id
                              AND j.status IN ('queued','running')
                        ),0) AS concurrent_jobs
                    FROM user_usage_limits l
                    WHERE l.user_id=%s::uuid
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

        if not row:
            return {"configured": True, "allowed": False, "reason": "usage_profile_missing"}

        (
            daily_limit,
            monthly_limit,
            concurrent_limit,
            is_suspended,
            suspension_reason,
            daily_jobs,
            monthly_seconds,
            concurrent_jobs,
        ) = row
        return {
            "configured": True,
            "allowed": (
                not is_suspended
                and daily_jobs < daily_limit
                and monthly_seconds < monthly_limit
                and concurrent_jobs < concurrent_limit
            ),
            "suspended": bool(is_suspended),
            "suspension_reason": suspension_reason,
            "limits": {
                "daily_jobs": daily_limit,
                "monthly_seconds": monthly_limit,
                "concurrent_jobs": concurrent_limit,
            },
            "usage": {
                "daily_jobs": daily_jobs,
                "monthly_seconds": monthly_seconds,
                "concurrent_jobs": concurrent_jobs,
            },
            "remaining": {
                "daily_jobs": max(0, daily_limit - daily_jobs),
                "monthly_seconds": max(0, monthly_limit - monthly_seconds),
                "concurrent_jobs": max(0, concurrent_limit - concurrent_jobs),
            },
        }

    def check(self, user_id: str, requested_seconds: int) -> Dict[str, Any]:
        state = self.status(user_id)
        if not state.get("configured"):
            return {"allowed": True, **state}

        limits = state["limits"]
        usage = state["usage"]

        reasons = []
        if state.get("suspended"):
            reasons.append("account_suspended")
        if usage["daily_jobs"] >= limits["daily_jobs"]:
            reasons.append("daily_job_limit_reached")
        if usage["monthly_seconds"] + requested_seconds > limits["monthly_seconds"]:
            reasons.append("monthly_generation_time_limit_reached")
        if usage["concurrent_jobs"] >= limits["concurrent_jobs"]:
            reasons.append("concurrent_job_limit_reached")

        return {
            **state,
            "allowed": not reasons,
            "reasons": reasons,
            "requested_seconds": requested_seconds,
        }

    def record_event(
        self,
        user_id: str,
        event_type: str,
        job_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        if not self.configured:
            return

        import json
        import psycopg

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO usage_events (user_id,job_id,event_type,metadata,created_at)
                    VALUES (%s::uuid,%s::uuid,%s,%s::jsonb,%s::timestamptz)
                    """,
                    (
                        user_id,
                        job_id,
                        event_type,
                        json.dumps(metadata or {}),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
