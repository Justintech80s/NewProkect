from __future__ import annotations

from typing import Any, Dict, List


class InstrumentationPlanner:
    """Chooses instrument roles using Production DNA + Music Brain context."""

    def build(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        dna = plan.get("producer_dna") or {}
        archetype = dna.get("archetype", "modern_minimal")
        context = plan.get("production_context") or {}

        suggested = [str(x) for x in (context.get("instruments") or [])][:8]

        defaults = {
            "polished_west_coast": [
                "tight acoustic/electronic drum blend",
                "round synth bass",
                "restrained synth lead",
                "electric piano",
                "subtle strings",
            ],
            "syncopated_futurist": [
                "unusual percussion",
                "short synth bass",
                "metallic texture",
                "minimal keyboard",
                "vocal-like percussion texture",
            ],
            "gritty_cinematic_sampler": [
                "dusty drums",
                "chopped cleared sample texture",
                "dark piano",
                "low strings",
                "filtered bass",
            ],
            "modern_minimal": [
                "punchy drums",
                "sub bass",
                "minimal keys",
                "ambient texture",
            ],
        }

        instruments: List[str] = []
        for item in suggested + defaults.get(archetype, defaults["modern_minimal"]):
            if item not in instruments:
                instruments.append(item)

        return {
            "archetype": archetype,
            "primary": instruments[:5],
            "secondary": instruments[5:10],
            "bass_prominence": dna.get("bass_prominence", 0.75),
            "arrangement_density": dna.get("arrangement_density", 0.50),
            "mix_polish": dna.get("mix_polish", 0.80),
        }

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        enriched["instrumentation_plan"] = self.build(enriched)
        return enriched
