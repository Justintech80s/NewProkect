from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class NoveltyEngine:
    """Creates controlled variation so remembered successes do not become a rut."""

    def apply(self, plan: Dict[str, Any], prompt: str, variation: int = 0) -> Dict[str, Any]:
        enriched = dict(plan)
        dna = dict(enriched.get("producer_dna") or {})
        seed = int(hashlib.sha256(f"{prompt}|{variation}".encode()).hexdigest()[:8], 16)

        dimensions = [
            ("swing", 0.08),
            ("syncopation", 0.10),
            ("negative_space", 0.10),
            ("percussion_complexity", 0.08),
            ("harmonic_complexity", 0.07),
            ("arrangement_density", 0.09),
            ("sample_chop_intensity", 0.08),
        ]
        changes = {}
        for index, (name, maximum) in enumerate(dimensions):
            if not isinstance(dna.get(name), (int, float)):
                continue
            raw = ((seed >> (index * 3)) & 7) / 7.0
            signed = (raw * 2.0) - 1.0
            delta = signed * maximum
            old = float(dna[name])
            new = max(0.0, min(1.0, old + delta))
            dna[name] = round(new, 4)
            changes[name] = round(new - old, 4)

        concepts = [
            "rhythmic pocket contrast",
            "instrument-role substitution",
            "section energy inversion",
            "call-and-response texture",
            "strategic negative space",
            "harmonic color variation",
            "percussion timbre contrast",
            "bass-register contrast",
        ]
        concept = concepts[seed % len(concepts)]

        dna["novelty_applied"] = True
        enriched["producer_dna"] = dna
        enriched["novelty"] = {
            "variation": variation,
            "concept": concept,
            "trait_changes": changes,
            "max_trait_shift": 0.10,
            "policy": "controlled-original-variation",
        }
        return enriched

    def candidate_variations(self, count: int = 3) -> List[int]:
        return list(range(max(1, min(int(count), 6))))
