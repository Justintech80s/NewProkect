from __future__ import annotations

from typing import Any, Dict, List


class HarmonyPlanner:
    """Builds harmonic conditioning from key, mood and Producer DNA."""

    def build(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        key = str(plan.get("key") or "C minor")
        dna = plan.get("producer_dna") or {}
        complexity = float(dna.get("harmonic_complexity", 0.45))
        mood = [str(x).lower() for x in (plan.get("mood") or [])]

        minor = "minor" in key.lower()
        if minor:
            progression = ["i", "VI", "III", "VII"]
        else:
            progression = ["I", "V", "vi", "IV"]

        if complexity > 0.65:
            voicings = ["7th", "add9", "sus2", "inversion"]
        elif complexity > 0.45:
            voicings = ["triad", "add9", "sus2"]
        else:
            voicings = ["triad", "power-interval"]

        tension = 0.72 if {"dark", "ominous"} & set(mood) else 0.48

        return {
            "key": key,
            "progression": progression,
            "voicings": voicings,
            "harmonic_complexity": round(complexity, 4),
            "tension": tension,
            "voice_leading": "smooth",
            "avoid_direct_melodic_copying": True,
        }

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        enriched["harmony_plan"] = self.build(enriched)
        return enriched
