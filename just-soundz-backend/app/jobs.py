from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .services.job_states import validate_transition


@dataclass
class Job:
    id: str
    status: str = "queued"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None


class JobStore:
    """Small in-process job registry with validated lifecycle transitions."""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(
        self,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Job:
        return self.create_with_id(
            str(uuid.uuid4()),
            user_id=user_id,
            request_id=request_id,
        )

    def create_with_id(
        self,
        job_id: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Job:
        job = Job(id=job_id, user_id=user_id, request_id=request_id)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes) -> Optional[Job]:
        allowed = set(Job.__dataclass_fields__)
        invalid = set(changes) - allowed
        if invalid:
            raise ValueError(f"unknown job fields: {','.join(sorted(invalid))}")

        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if "status" in changes:
                validate_transition(job.status, str(changes["status"]))
            for key, value in changes.items():
                setattr(job, key, value)
            return job


jobs = JobStore()
