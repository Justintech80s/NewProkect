from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class WorkerCircuitBreaker:
    """Temporarily removes repeatedly failing remote workers from routing."""

    def __init__(self):
        self.failure_threshold = int(os.getenv("JUST_MAKER_CIRCUIT_FAILURE_THRESHOLD", "3"))
        self.reset_seconds = int(os.getenv("JUST_MAKER_CIRCUIT_RESET_SECONDS", "120"))
        self._states: Dict[str, CircuitState] = {}
        self._lock = threading.Lock()

    def allow(self, worker_name: str) -> bool:
        with self._lock:
            state = self._states.get(worker_name)
            if not state or state.opened_at is None:
                return True
            if time.time() - state.opened_at >= self.reset_seconds:
                state.failures = 0
                state.opened_at = None
                return True
            return False

    def success(self, worker_name: str) -> None:
        with self._lock:
            self._states[worker_name] = CircuitState()

    def failure(self, worker_name: str) -> None:
        with self._lock:
            state = self._states.setdefault(worker_name, CircuitState())
            state.failures += 1
            if state.failures >= self.failure_threshold:
                state.opened_at = time.time()

    def status(self) -> Dict[str, dict]:
        with self._lock:
            now = time.time()
            return {
                name: {
                    "failures": state.failures,
                    "open": bool(
                        state.opened_at is not None
                        and now - state.opened_at < self.reset_seconds
                    ),
                    "reset_in_seconds": (
                        max(0, int(self.reset_seconds - (now - state.opened_at)))
                        if state.opened_at is not None
                        else 0
                    ),
                }
                for name, state in self._states.items()
            }
