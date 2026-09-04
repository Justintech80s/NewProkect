from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


class JobRecoveryPlanner:
    """Determines whether failed/stale generation jobs may be retried safely."""

    RETRYABLE_STATUSES = {"failed", "stalled"}

    def assess(self, job: Dict[str, Any]) -> Dict[str, Any]:
        status = str(job.get("status") or "")
        retry_count = int(job.get("retry_count") or 0)
        max_retries = int(job.get("max_retries") or 3)

        retryable = status in self.RETRYABLE_STATUSES and retry_count < max_retries
        return {
            "retryable": retryable,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "reason": (
                "retry_allowed"
                if retryable
                else "retry_limit_reached"
                if retry_count >= max_retries
                else "job_not_in_retryable_state"
            ),
        }

    def retry_payload(self, job: Dict[str, Any]) -> Dict[str, Any]:
        assessment = self.assess(job)
        if not assessment["retryable"]:
            raise ValueError(assessment["reason"])

        return {
            "request": dict(job.get("request") or {}),
            "retry_of": job.get("job_id"),
            "retry_count": assessment["retry_count"] + 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
