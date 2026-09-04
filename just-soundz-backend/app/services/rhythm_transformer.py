from __future__ import annotations

from typing import Any, Dict, List


class RhythmTransformer:
    """Builds beat-event conditioning from Producer DNA controls."""

    STEPS = 16

    def build(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        dna = plan.get("producer_dna") or {}
        swing = float(dna.get("swing", 0.52))
        syncopation = float(dna.get("syncopation", 0.50))
        kick_density = float(dna.get("kick_density", 0.32))
        snare_density = float(dna.get("snare_density", 0.18))
        perc_complexity = float(dna.get("percussion_complexity", 0.50))

        kick = self._kick_pattern(kick_density, syncopation)
        snare = self._snare_pattern(snare_density)
        hats = self._hat_pattern(swing, perc_complexity)
        percussion = self._percussion_pattern(syncopation, perc_complexity)

        return {
            "grid": "16-step",
            "swing": round(swing, 4),
            "microtiming_ms": self._microtiming(swing),
            "kick": kick,
            "snare": snare,
            "hats": hats,
            "percussion": percussion,
            "humanization": {
                "velocity_variance": round(0.04 + 0.12 * perc_complexity, 4),
                "timing_variance_ms": round(2.0 + 8.0 * swing, 2),
            },
        }

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        enriched["rhythm_plan"] = self.build(enriched)
        return enriched

    def _kick_pattern(self, density: float, syncopation: float) -> List[Dict[str, Any]]:
        steps = [0, 8]
        if density > 0.30:
            steps.append(6 if syncopation > 0.60 else 10)
        if density > 0.40:
            steps.append(14)
        return [
            {"step": s, "velocity": round(1.0 - 0.08 * i, 3)}
            for i, s in enumerate(sorted(set(steps)))
        ]

    def _snare_pattern(self, density: float) -> List[Dict[str, Any]]:
        steps = [4, 12]
        if density > 0.22:
            steps.append(15)
        return [
            {"step": s, "velocity": 0.96 if s in (4, 12) else 0.58}
            for s in sorted(set(steps))
        ]

    def _hat_pattern(self, swing: float, complexity: float) -> Dict[str, Any]:
        base = list(range(0, self.STEPS, 2))
        if complexity > 0.68:
            base += [3, 7, 11, 15]
        return {
            "steps": sorted(set(base)),
            "swing": round(swing, 4),
            "velocity_curve": "alternating",
        }

    def _percussion_pattern(self, syncopation: float, complexity: float) -> List[int]:
        steps = []
        if complexity > 0.40:
            steps += [3, 11]
        if syncopation > 0.70:
            steps += [6, 14]
        if complexity > 0.80:
            steps += [1, 9]
        return sorted(set(steps))

    def _microtiming(self, swing: float) -> Dict[str, float]:
        amount = max(0.0, min(1.0, (swing - 0.50) * 2.0))
        return {
            "even_steps": 0.0,
            "offbeat_steps": round(4.0 + 18.0 * amount, 2),
        }
