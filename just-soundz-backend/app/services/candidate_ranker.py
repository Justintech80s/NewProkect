from __future__ import annotations

from typing import Any, Dict, List


class CandidateRanker:
    """Ranks already-evaluated creative candidates without changing the evaluator."""

    def rank(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked = []
        for candidate in candidates:
            evaluation = candidate.get("evaluation") or {}
            production = candidate.get("production_critic") or {}
            repetition = candidate.get("repetition") or {}
            mastering = candidate.get("mastering") or {}
            score = float(evaluation.get("score") or 0.0)

            # Small tie-breakers reward production readiness and penalize repetition.
            if production.get("pass"):
                score += 0.025
            if (mastering.get("critic") or {}).get("pass"):
                score += 0.015
            if repetition.get("too_repetitive"):
                score -= 0.06

            ranked.append({
                "variation": int(candidate.get("variation", 0)),
                "selection_score": round(max(0.0, min(1.0, score)), 4),
                "evaluation_score": round(float(evaluation.get("score") or 0.0), 4),
                "grade": evaluation.get("grade"),
                "passed": bool(evaluation.get("pass")),
                "candidate": candidate,
            })

        ranked.sort(
            key=lambda item: (
                item["passed"],
                item["selection_score"],
                item["evaluation_score"],
            ),
            reverse=True,
        )
        return ranked

    def summary(self, ranked: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{
            "variation": item["variation"],
            "selection_score": item["selection_score"],
            "evaluation_score": item["evaluation_score"],
            "grade": item["grade"],
            "passed": item["passed"],
        } for item in ranked]
