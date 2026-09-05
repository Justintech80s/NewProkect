from __future__ import annotations

from typing import Any, Dict, List


class GenerationEvaluator:
    """Builds a repeatable quality scorecard for every generation."""

    WEIGHTS = {
        "prompt_adherence": 0.20,
        "tempo_accuracy": 0.12,
        "key_accuracy": 0.10,
        "variation": 0.12,
        "mastering": 0.14,
        "stem_completeness": 0.10,
        "artifact_integrity": 0.08,
        "conditioning": 0.08,
        "provider_health": 0.06,
    }

    def evaluate(
        self,
        *,
        plan: Dict[str, Any],
        generation: Dict[str, Any],
        analysis: Dict[str, Any],
        quality: Dict[str, Any],
        repetition: Dict[str, Any],
        mastering: Dict[str, Any],
        stems: Dict[str, Any],
        artifacts: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        scores = {
            "prompt_adherence": self._prompt(quality),
            "tempo_accuracy": self._tempo(plan, analysis),
            "key_accuracy": self._key(plan, analysis),
            "variation": self._variation(repetition),
            "mastering": self._mastering(mastering),
            "stem_completeness": self._stems(stems),
            "artifact_integrity": self._artifacts(artifacts or []),
            "conditioning": self._conditioning(plan),
            "provider_health": self._provider(generation),
        }

        weighted = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        issues = self._issues(scores)

        return {
            "score": round(weighted, 4),
            "grade": self._grade(weighted),
            "pass": weighted >= 0.75,
            "scores": {k: round(v, 4) for k, v in scores.items()},
            "weights": self.WEIGHTS,
            "issues": issues,
            "provider": generation.get("provider"),
            "routing": generation.get("routing") or {},
        }

    def _prompt(self, quality: Dict[str, Any]) -> float:
        if quality.get("prompt_match") is not None:
            return self._clamp(float(quality["prompt_match"]))
        return self._clamp(float(quality.get("score") or 0.55))

    def _tempo(self, plan: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        target = plan.get("bpm")
        actual = analysis.get("bpm")
        if not target or not actual:
            return 0.55
        delta = abs(float(target) - float(actual))
        return self._clamp(1.0 - delta / 18.0)

    def _key(self, plan: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        target = str(plan.get("key") or "").lower()
        actual = str(analysis.get("key") or "").lower()
        if not target or not actual:
            return 0.55
        return 1.0 if target.startswith(actual) or actual.startswith(target) else 0.4

    def _variation(self, repetition: Dict[str, Any]) -> float:
        if repetition.get("too_repetitive"):
            return 0.35
        score = float(repetition.get("score") or 0.0)
        return self._clamp(1.0 - max(0.0, score - 0.55))

    def _mastering(self, mastering: Dict[str, Any]) -> float:
        critic = mastering.get("critic") or {}
        if critic.get("score") is not None:
            return self._clamp(float(critic["score"]))
        return 0.8 if mastering.get("mastered") else 0.3

    def _stems(self, stems: Dict[str, Any]) -> float:
        if not stems.get("enabled"):
            return 0.6
        generated = stems.get("generated") or []
        if generated:
            count = len(generated)
            return self._clamp(count / 6.0)
        if stems.get("engine"):
            return 0.75
        return 0.4

    def _artifacts(self, artifacts: List[Dict[str, Any]]) -> float:
        if not artifacts:
            return 0.55
        valid = 0
        for item in artifacts:
            if item.get("sha256") and item.get("size_bytes", 0) > 0:
                valid += 1
        return self._clamp(valid / max(1, len(artifacts)))

    def _conditioning(self, plan: Dict[str, Any]) -> float:
        conditioning = plan.get("conditioning") or {}
        expected = [
            "text", "musical", "rhythm", "production",
            "instrumentation", "arrangement", "advanced_controls",
        ]
        present = sum(1 for k in expected if conditioning.get(k))
        return present / len(expected)

    def _provider(self, generation: Dict[str, Any]) -> float:
        routing = generation.get("routing") or {}
        attempts = routing.get("attempts") or []
        if generation.get("provider") == "unavailable":
            return 0.0
        failures = sum(1 for x in attempts if x.get("status") == "failed")
        return self._clamp(1.0 - 0.15 * failures)

    def _issues(self, scores: Dict[str, float]) -> List[str]:
        return [
            key for key, value in scores.items()
            if value < 0.65
        ]

    def _grade(self, score: float) -> str:
        if score >= 0.90:
            return "A"
        if score >= 0.82:
            return "B"
        if score >= 0.75:
            return "C"
        if score >= 0.65:
            return "D"
        return "F"

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
