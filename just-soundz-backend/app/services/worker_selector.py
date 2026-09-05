from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from .capabilities import CapabilityRequirements
from .model_registry import ModelRegistry, WorkerConfig
from .worker_performance import WorkerPerformanceStore


class WorkerSelector:
    """Ranks workers by conditioning coverage, duration support and priority."""

    def __init__(
        self,
        registry: ModelRegistry | None = None,
        performance: WorkerPerformanceStore | None = None,
    ):
        self.registry = registry or ModelRegistry()
        self.requirements = CapabilityRequirements()
        self.performance = performance or WorkerPerformanceStore()

    def rank(self, plan: Dict[str, Any]) -> List[Tuple[WorkerConfig, Dict[str, Any]]]:
        required = self.requirements.required(plan)
        duration = int(plan.get("duration_seconds") or 0)
        ranked = []
        global_summaries = self.performance.summary()
        routing_context = self.performance.context_key(plan)
        contextual_summaries = self.performance.summary(context=routing_context)
        genre = str(plan.get("genre") or "").strip().lower()

        for worker in self.registry.workers():
            coverage = worker.capabilities.coverage(required)
            duration_ok = duration <= worker.capabilities.max_duration_seconds
            built_in_penalty = 0.25 if worker.kind == "built-in-procedural" else 0.0

            global_history = self.performance.routing_bonus(
                worker.name,
                summaries=global_summaries,
            )
            contextual_history = self.performance.routing_bonus(
                worker.name,
                summaries=contextual_summaries,
            )
            historical_bonus = min(
                0.14,
                float(global_history.get("bonus") or 0.0) * 0.45
                + float(contextual_history.get("bonus") or 0.0) * 0.75,
            )

            specialization_bonus = self._specialization_bonus(worker.name, genre)

            score = (
                coverage * 0.80
                + (0.15 if duration_ok else 0.0)
                + max(0.0, 0.05 - worker.priority / 10000.0)
                + historical_bonus
                + specialization_bonus
                - built_in_penalty
            )

            ranked.append((worker, {
                "score": round(score, 4),
                "coverage": round(coverage, 4),
                "duration_ok": duration_ok,
                "required_capabilities": required,
                "historical_bonus": round(historical_bonus, 4),
                "specialization_bonus": round(specialization_bonus, 4),
                "global_performance": global_history.get("history", {}),
                "contextual_performance": contextual_history.get("history", {}),
                "routing_context": routing_context,
                "historical_reason": (
                    "contextual_quality"
                    if contextual_history.get("bonus", 0.0) > 0
                    else global_history.get("reason")
                ),
            }))

        ranked.sort(key=lambda item: item[1]["score"], reverse=True)
        return ranked

    def _specialization_bonus(self, worker_name: str, genre: str) -> float:
        if not genre:
            return 0.0
        key = worker_name.upper().replace("-", "_")
        raw = os.getenv(f"JUST_MAKER_{key}_GENRES", "")
        genres = {
            value.strip().lower()
            for value in raw.split(",")
            if value.strip()
        }
        return 0.08 if genre in genres else 0.0
