from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


class JobRecoveryPlanner:
    """Determines whether failed or stale-running jobs may be retried safely."""

    def __init__(self, stale_after_seconds: int = 900):
        self.stale_after_seconds = max(30, min(int(stale_after_seconds), 86400))

    def _is_stale_running(self, job: Dict[str, Any]) -> bool:
        if str(job.get("status") or "") != "running":
            return False
        raw = job.get("heartbeat_at")
        if not raw:
            return False
        try:
            heartbeat = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        except ValueError:
            return False
        age = (datetime.now(timezone.utc) - heartbeat.astimezone(timezone.utc)).total_seconds()
        return age >= self.stale_after_seconds

    def assess(self, job: Dict[str, Any]) -> Dict[str, Any]:
        status = str(job.get("status") or "")
        retry_count = int(job.get("retry_count") or 0)
        max_retries = int(job.get("max_retries") or 3)

        if retry_count >= max_retries:
            retryable = False
            reason = "retry_limit_reached"
        elif status == "failed":
            retryable = True
            reason = "retry_allowed"
        elif self._is_stale_running(job):
            retryable = True
            reason = "stale_running_job"
        else:
            retryable = False
            reason = "job_not_in_retryable_state"

        return {
            "retryable": retryable,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "reason": reason,
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
