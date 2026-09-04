from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Job:
    id: str
    status: str = "queued"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class JobStore:
    """Small in-process job registry.

    This preserves a stable API contract now. In production it can be replaced
    by Redis/Postgres without changing the frontend endpoints.
    """

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self) -> Job:
        return self.create_with_id(str(uuid.uuid4()))

    def create_with_id(self, job_id: str) -> Job:
        job = Job(id=job_id)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            for key, value in changes.items():
                setattr(job, key, value)
            return job


jobs = JobStore()
