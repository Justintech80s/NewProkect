from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .capabilities import CapabilityRequirements
from .model_registry import ModelRegistry, WorkerConfig


class WorkerSelector:
    """Ranks workers by conditioning coverage, duration support and priority."""

    def __init__(self, registry: ModelRegistry | None = None):
        self.registry = registry or ModelRegistry()
        self.requirements = CapabilityRequirements()

    def rank(self, plan: Dict[str, Any]) -> List[Tuple[WorkerConfig, Dict[str, Any]]]:
        required = self.requirements.required(plan)
        duration = int(plan.get("duration_seconds") or 0)
        ranked = []

        for worker in self.registry.workers():
            coverage = worker.capabilities.coverage(required)
            duration_ok = duration <= worker.capabilities.max_duration_seconds
            built_in_penalty = 0.25 if worker.kind == "built-in-procedural" else 0.0

            score = (
                coverage * 0.80
                + (0.15 if duration_ok else 0.0)
                + max(0.0, 0.05 - worker.priority / 10000.0)
                - built_in_penalty
            )

            ranked.append((worker, {
                "score": round(score, 4),
                "coverage": round(coverage, 4),
                "duration_ok": duration_ok,
                "required_capabilities": required,
            }))

        ranked.sort(key=lambda item: item[1]["score"], reverse=True)
        return ranked
