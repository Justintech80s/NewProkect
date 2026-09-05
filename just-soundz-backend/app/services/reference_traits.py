from __future__ import annotations

from typing import Any, Dict


class ReferenceTraitBlender:
    """Blends broad cleared-reference production traits into Producer DNA."""

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        reference = enriched.get("reference_audio") or {}
        traits = reference.get("production_traits") or {}
        if not traits:
            return enriched

        dna = dict(enriched.get("producer_dna") or {})

        dna["bass_prominence"] = self._blend(
            dna.get("bass_prominence", 0.75),
            traits.get("low_end_weight"),
            0.30,
        )
        dna["percussion_complexity"] = self._blend(
            dna.get("percussion_complexity", 0.50),
            traits.get("rhythmic_density"),
            0.22,
        )
        dna["mix_polish"] = self._blend(
            dna.get("mix_polish", 0.80),
            traits.get("mix_polish_hint"),
            0.25,
        )
        dna["negative_space"] = self._blend(
            dna.get("negative_space", 0.50),
            1.0 - float(traits.get("rhythmic_density", 0.5)),
            0.18,
        )
        dna["transient_punch"] = round(float(traits.get("transient_punch", 0.5)), 4)
        dna["brightness"] = round(float(traits.get("brightness", 0.5)), 4)
        dna["dynamic_range"] = round(float(traits.get("dynamic_range", 0.5)), 4)
        dna["reference_trait_blend"] = True
        dna["reference_policy"] = "production-traits-only-no-melody-copy"

        enriched["producer_dna"] = dna
        return enriched

    def _blend(self, base: Any, reference: Any, weight: float) -> float:
        base_value = float(base)
        if reference is None:
            return round(base_value, 4)
        ref_value = float(reference)
        value = base_value * (1.0 - weight) + ref_value * weight
        return round(max(0.0, min(1.0, value)), 4)
