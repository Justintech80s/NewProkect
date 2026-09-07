from __future__ import annotations

from typing import Any, Dict, List


class MasteringCritic:
    """Deterministic delivery thresholds with a bounded corrective policy."""

    PEAK_MIN_DBFS = -1.5
    PEAK_MAX_DBFS = -0.3
    RMS_MIN_DBFS = -20.0
    RMS_MAX_DBFS = -7.0
    CREST_FACTOR_MIN = 1.4
    MAX_CORRECTIVE_PASSES = 1

    def evaluate(self, mastering: Dict[str, Any]) -> Dict[str, Any]:
        if not mastering.get("mastered"):
            return {
                "pass": False,
                "issues": ["not_mastered"],
                "score": 0.0,
                "corrective_pass_allowed": False,
            }

        issues: List[str] = []
        peak = float(mastering.get("peak_dbfs", 0.0))
        rms = float(mastering.get("rms_dbfs", -99.0))
        crest = float(mastering.get("crest_factor", 0.0))

        if peak > self.PEAK_MAX_DBFS:
            issues.append("peak_too_hot")
        if peak < -3.0:
            issues.append("peak_too_low")
        if rms > self.RMS_MAX_DBFS:
            issues.append("over_compressed")
        if rms < self.RMS_MIN_DBFS:
            issues.append("master_too_quiet")
        if crest < self.CREST_FACTOR_MIN:
            issues.append("insufficient_dynamics")

        score = max(0.0, 1.0 - 0.16 * len(issues))
        return {
            "pass": not issues,
            "issues": issues,
            "score": round(score, 4),
            "corrective_pass_allowed": bool(issues),
            "max_corrective_passes": self.MAX_CORRECTIVE_PASSES,
            "targets": {
                "peak_dbfs": [self.PEAK_MIN_DBFS, self.PEAK_MAX_DBFS],
                "rms_dbfs": [self.RMS_MIN_DBFS, self.RMS_MAX_DBFS],
                "crest_factor_min": self.CREST_FACTOR_MIN,
            },
        }

    def should_correct(self, critique: Dict[str, Any], completed_passes: int) -> bool:
        return (
            not critique.get("pass", False)
            and completed_passes < self.MAX_CORRECTIVE_PASSES
        )

    def corrective_target_peak(self, critique: Dict[str, Any]) -> float:
        issues = set(critique.get("issues") or [])
        if "peak_too_hot" in issues:
            return -1.2
        if "peak_too_low" in issues:
            return -0.8
        return -1.0
