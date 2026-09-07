from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from .security import normalize_uuid


def owned_job(
    job_id: str,
    user_id: str,
    *,
    durable_store,
    memory_store,
) -> Optional[Dict[str, Any]]:
    """Resolve a job only inside the authenticated user's ownership boundary."""
    try:
        normalized = normalize_uuid(job_id)
    except ValueError:
        return None

    if durable_store.configured:
        return durable_store.get(normalized, user_id=user_id)

    job = memory_store.get(normalized)
    if not job or job.user_id != user_id:
        return None

    payload = asdict(job)
    return {
        "job_id": payload["id"],
        "status": payload["status"],
        "stage": payload["status"],
        "progress": 1.0 if payload["status"] == "complete" else 0.0,
        "result": payload["result"],
        "error": payload["error"],
        "user_id": payload["user_id"],
        "request_id": payload.get("request_id"),
        "artifacts": [],
    }
