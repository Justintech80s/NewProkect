from __future__ import annotations

from typing import Any, Dict, List


class ProductionCritic:
    """Scores how well a render follows the production plan using available evidence."""

    def evaluate(
        self,
        plan: Dict[str, Any],
        analysis: Dict[str, Any],
        repetition: Dict[str, Any],
        mastering: Dict[str, Any],
    ) -> Dict[str, Any]:
        scores: Dict[str, float] = {}
        issues: List[str] = []

        target_bpm = plan.get("bpm")
        actual_bpm = analysis.get("bpm")
        if target_bpm and actual_bpm:
            delta = abs(float(target_bpm) - float(actual_bpm))
            scores["tempo"] = max(0.0, 1.0 - delta / 20.0)
            if delta > 5:
                issues.append("tempo_mismatch")
        else:
            scores["tempo"] = 0.60

        target_key = str(plan.get("key") or "").lower()
        actual_key = str(analysis.get("key") or "").lower()
        if target_key and actual_key:
            scores["key"] = 1.0 if target_key.startswith(actual_key) or actual_key.startswith(target_key) else 0.45
            if scores["key"] < 0.7:
                issues.append("key_mismatch")
        else:
            scores["key"] = 0.60

        rep = float(repetition.get("score") or 0.0)
        scores["variation"] = max(0.0, min(1.0, 1.0 - max(0.0, rep - 0.60)))
        if repetition.get("too_repetitive"):
            issues.append("excessive_repetition")

        if mastering.get("mastered"):
            peak = float(mastering.get("peak_dbfs", -1.0))
            scores["mastering"] = 1.0 if -1.5 <= peak <= -0.3 else 0.72
        else:
            scores["mastering"] = 0.45
            issues.append("not_mastered")

        dna = plan.get("producer_dna") or {}
        conditioning = plan.get("conditioning") or {}
        scores["conditioning_completeness"] = self._conditioning_score(conditioning)
        scores["producer_dna_completeness"] = self._dna_score(dna)

        total = sum(scores.values()) / max(len(scores), 1)
        return {
            "score": round(total, 4),
            "scores": {k: round(v, 4) for k, v in scores.items()},
            "issues": issues,
            "pass": total >= 0.72 and not repetition.get("too_repetitive", False),
            "repair_priority": self._priority(issues),
        }

    def repair_instructions(self, critique: Dict[str, Any]) -> Dict[str, Any]:
        issues = critique.get("issues") or []
        instructions: Dict[str, Any] = {}
        if "tempo_mismatch" in issues:
            instructions["tempo"] = "increase BPM adherence"
        if "key_mismatch" in issues:
            instructions["harmony"] = "strengthen tonic/key conditioning"
        if "excessive_repetition" in issues:
            instructions["arrangement"] = "increase section contrast and rhythmic variation"
        if "not_mastered" in issues:
            instructions["mastering"] = "run mastering chain"
        return instructions

    def _conditioning_score(self, conditioning: Dict[str, Any]) -> float:
        expected = ["text", "musical", "rhythm", "production", "instrumentation", "arrangement"]
        present = sum(1 for k in expected if conditioning.get(k))
        return present / len(expected)

    def _dna_score(self, dna: Dict[str, Any]) -> float:
        expected = [
            "swing", "syncopation", "negative_space", "kick_density",
            "bass_prominence", "sample_chop_intensity", "mix_polish",
        ]
        present = sum(1 for k in expected if dna.get(k) is not None)
        return present / len(expected)

    def _priority(self, issues: List[str]) -> List[str]:
        order = ["tempo_mismatch", "key_mismatch", "excessive_repetition", "not_mastered"]
        return [x for x in order if x in issues]
