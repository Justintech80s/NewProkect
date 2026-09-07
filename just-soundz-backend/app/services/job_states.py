from __future__ import annotations

from types import MappingProxyType


class JobStateError(ValueError):
    """Raised when a generation job attempts an illegal state change."""


LEGAL_TRANSITIONS = MappingProxyType({
    "queued": frozenset({"queued", "running", "failed"}),
    "running": frozenset({"running", "complete", "failed"}),
    "complete": frozenset({"complete"}),
    "failed": frozenset({"failed"}),
})


def validate_transition(current: str, target: str) -> str:
    if current not in LEGAL_TRANSITIONS:
        raise JobStateError(f"unknown current job state: {current}")
    if target not in LEGAL_TRANSITIONS:
        raise JobStateError(f"unknown target job state: {target}")
    if target not in LEGAL_TRANSITIONS[current]:
        raise JobStateError(f"illegal job state transition: {current}->{target}")
    return target


def normalize_progress(status: str, progress: float | None) -> float | None:
    if status not in LEGAL_TRANSITIONS:
        raise JobStateError(f"unknown job state: {status}")
    if status == "complete":
        return 1.0
    if progress is None:
        return None
    return max(0.0, min(1.0, float(progress)))
