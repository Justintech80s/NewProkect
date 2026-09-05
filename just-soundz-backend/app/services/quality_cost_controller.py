from __future__ import annotations

from typing import Any, Dict


class QualityCostController:
    """Estimates render effort and constrains candidate fan-out to a caller budget."""

    def __init__(self, operations):
        self.operations = operations

    def plan(
        self,
        *,
        duration_seconds: int,
        candidate_count: int,
        make_stems: bool,
        max_estimated_cost_usd: float | None,
    ) -> Dict[str, Any]:
        requested = max(1, min(int(candidate_count), 3))
        stem_count = 4 if make_stems else 1

        per_candidate = self.operations.estimate_generation_cost(
            duration_seconds=duration_seconds,
            attempts=1,
            stem_count=stem_count,
        )
        estimated = round(per_candidate * requested, 6)

        if max_estimated_cost_usd is None:
            return {
                "candidate_count": requested,
                "estimated_cost_usd": estimated,
                "per_candidate_estimated_cost_usd": per_candidate,
                "budget_limited": False,
            }

        budget = max(0.0, float(max_estimated_cost_usd))
        affordable = int(budget // max(per_candidate, 1e-9))
        chosen = max(1, min(requested, affordable if affordable > 0 else 1))

        return {
            "candidate_count": chosen,
            "estimated_cost_usd": round(per_candidate * chosen, 6),
            "per_candidate_estimated_cost_usd": per_candidate,
            "max_estimated_cost_usd": round(budget, 6),
            "budget_limited": chosen < requested,
            "budget_below_single_candidate_estimate": budget < per_candidate,
        }
