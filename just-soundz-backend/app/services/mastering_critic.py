from __future__ import annotations

from typing import Any, Dict, List


class MasteringCritic:
    """Checks whether a master falls inside practical delivery targets."""

    def evaluate(self, mastering: Dict[str, Any]) -> Dict[str, Any]:
        if not mastering.get("mastered"):
            return {
                "pass": False,
                "issues": ["not_mastered"],
                "score": 0.0,
            }

        issues: List[str] = []
        peak = float(mastering.get("peak_dbfs", 0.0))
        rms = float(mastering.get("rms_dbfs", -99.0))
        crest = float(mastering.get("crest_factor", 0.0))

        if peak > -0.3:
            issues.append("peak_too_hot")
        if peak < -3.0:
            issues.append("peak_too_low")
        if rms > -7.0:
            issues.append("over_compressed")
        if rms < -20.0:
            issues.append("master_too_quiet")
        if crest < 1.4:
            issues.append("insufficient_dynamics")

        score = max(0.0, 1.0 - 0.16 * len(issues))
        return {
            "pass": not issues,
            "issues": issues,
            "score": round(score, 4),
            "targets": {
                "peak_dbfs": [-1.5, -0.3],
                "rms_dbfs": [-20.0, -7.0],
                "crest_factor_min": 1.4,
            },
        }

    def corrective_target_peak(self, critique: Dict[str, Any]) -> float:
        issues = set(critique.get("issues") or [])
        if "peak_too_hot" in issues:
            return -1.2
        if "peak_too_low" in issues:
            return -0.8
        return -1.0
