from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class OrchestrationPolicy:
    """Bounded production routing policy for generation workers."""

    max_worker_attempts: int
    health_timeout_seconds: float
    retryable_failures: int

    @classmethod
    def from_env(cls) -> "OrchestrationPolicy":
        return cls(
            max_worker_attempts=max(
                1, min(int(os.getenv("JUST_MAKER_MAX_WORKER_ATTEMPTS", "4")), 12)
            ),
            health_timeout_seconds=max(
                0.25,
                min(float(os.getenv("JUST_MAKER_WORKER_HEALTH_TIMEOUT_SECONDS", "2.5")), 30.0),
            ),
            retryable_failures=max(
                0, min(int(os.getenv("JUST_MAKER_RETRYABLE_FAILURES", "1")), 5)
            ),
        )

    def should_attempt(self, attempts: List[Dict[str, Any]]) -> bool:
        actual = sum(
            1
            for attempt in attempts
            if attempt.get("status") in {"failed", "success"}
        )
        return actual < self.max_worker_attempts

    def audit(self, attempts: List[Dict[str, Any]], *, started_at: float) -> Dict[str, Any]:
        failures = sum(1 for item in attempts if item.get("status") == "failed")
        skipped = sum(1 for item in attempts if item.get("status") == "skipped")
        successes = sum(1 for item in attempts if item.get("status") == "success")
        return {
            "policy": "pass5-v1",
            "max_worker_attempts": self.max_worker_attempts,
            "retryable_failures": self.retryable_failures,
            "health_timeout_seconds": self.health_timeout_seconds,
            "attempted": failures + successes,
            "failures": failures,
            "skipped": skipped,
            "successes": successes,
            "elapsed_seconds": round(max(0.0, time.time() - started_at), 3),
        }
