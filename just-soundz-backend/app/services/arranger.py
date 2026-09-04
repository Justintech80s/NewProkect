from __future__ import annotations

from typing import Any, Dict, List


class ArrangementEngine:
    """Builds a dynamic song structure from the producer plan."""

    ENERGY = {
        "intro": 0.35,
        "verse": 0.55,
        "prehook": 0.72,
        "hook": 0.95,
        "bridge": 0.48,
        "breakdown": 0.40,
        "outro": 0.30,
    }

    def build(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        sections = plan.get("arrangement") or []
        out = []
        for index, section in enumerate(sections):
            name = str(section.get("section", "verse")).lower()
            energy = float(section.get("energy", self.ENERGY.get(name, 0.55)))
            out.append({
                "index": index,
                "section": name,
                "bars": int(section.get("bars", 8)),
                "energy": max(0.1, min(1.0, energy)),
                "variation": index,
                "drum_density": self._drum_density(name, energy),
                "harmonic_motion": self._harmonic_motion(name),
            })
        return out

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        enriched["arrangement"] = self.build(plan)
        return enriched

    def _drum_density(self, name: str, energy: float) -> str:
        if name in {"intro", "breakdown", "outro"}:
            return "sparse"
        if energy >= 0.85:
            return "full"
        return "medium"

    def _harmonic_motion(self, name: str) -> str:
        if name in {"hook", "prehook"}:
            return "lift"
        if name in {"bridge", "breakdown"}:
            return "contrast"
        return "stable"
