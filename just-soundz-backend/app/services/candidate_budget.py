from __future__ import annotations

from typing import Any, Dict


class CandidateBudgetPlanner:
    """Chooses a bounded candidate count from request difficulty and quality target."""

    def decide(
        self,
        *,
        requested_count: int,
        quality_threshold: float,
        duration_seconds: int,
        make_stems: bool,
        prompt: str,
        mode: str = "manual",
    ) -> Dict[str, Any]:
        requested = max(1, min(int(requested_count), 3))
        if mode != "adaptive":
            return {
                "mode": "manual",
                "candidate_count": requested,
                "reasons": ["explicit_candidate_count"],
            }

        score = 0
        reasons = []
        text = (prompt or "").lower()

        if quality_threshold >= 0.82:
            score += 2
            reasons.append("high_quality_target")
        elif quality_threshold >= 0.76:
            score += 1
            reasons.append("elevated_quality_target")

        if duration_seconds >= 240:
            score += 1
            reasons.append("long_form_generation")

        complexity_terms = (
            "cinematic", "orchestral", "complex", "experimental",
            "switch", "evolving", "multi-section", "soundtrack",
        )
        if any(term in text for term in complexity_terms):
            score += 1
            reasons.append("complex_prompt")

        # Stems multiply render work, so don't automatically spend the full budget
        # unless the quality/complexity signal is strong.
        if make_stems and score < 3:
            score = min(score, 1)
            reasons.append("stem_compute_guard")

        chosen = 1 if score <= 0 else 2 if score <= 2 else 3
        chosen = min(chosen, requested)

        return {
            "mode": "adaptive",
            "candidate_count": chosen,
            "requested_max": requested,
            "difficulty_score": score,
            "reasons": reasons or ["standard_generation"],
        }
