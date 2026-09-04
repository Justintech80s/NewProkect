from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


class SelfRepairEngine:
    """Turns Production Critic findings into concrete plan/conditioning changes."""

    def apply(
        self,
        plan: Dict[str, Any],
        critique: Dict[str, Any],
        attempt: int,
    ) -> Dict[str, Any]:
        repaired = deepcopy(plan)
        issues = critique.get("issues") or []
        repaired["self_repair_attempt"] = attempt
        repaired["self_repair_source_score"] = critique.get("score")

        if "tempo_mismatch" in issues:
            repaired = self._repair_tempo(repaired, attempt)

        if "key_mismatch" in issues:
            repaired = self._repair_key(repaired, attempt)

        if "excessive_repetition" in issues:
            repaired = self._repair_variation(repaired, attempt)

        if "not_mastered" in issues:
            repaired.setdefault("mastering_instructions", {})
            repaired["mastering_instructions"]["force_mastering"] = True

        repaired.setdefault("negative_instructions", [])
        marker = "prioritize adherence to repair instructions"
        if marker not in repaired["negative_instructions"]:
            repaired["negative_instructions"].append(marker)

        return repaired

    def _repair_tempo(self, plan: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        rhythm = dict(plan.get("rhythm_plan") or {})
        rhythm["tempo_lock"] = True
        rhythm["tempo_strength"] = min(1.0, 0.82 + 0.08 * attempt)
        plan["rhythm_plan"] = rhythm

        conditioning = dict(plan.get("conditioning") or {})
        musical = dict(conditioning.get("musical") or {})
        musical["bpm"] = plan.get("bpm")
        musical["tempo_lock"] = True
        musical["tempo_strength"] = rhythm["tempo_strength"]
        conditioning["musical"] = musical
        plan["conditioning"] = conditioning
        return plan

    def _repair_key(self, plan: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        harmony = dict(plan.get("harmony_plan") or {})
        harmony["key"] = plan.get("key")
        harmony["tonic_emphasis"] = min(1.0, 0.78 + 0.10 * attempt)
        harmony["cadence_strength"] = "strong"
        plan["harmony_plan"] = harmony

        conditioning = dict(plan.get("conditioning") or {})
        musical = dict(conditioning.get("musical") or {})
        musical["key"] = plan.get("key")
        musical["harmony"] = harmony
        conditioning["musical"] = musical
        plan["conditioning"] = conditioning
        return plan

    def _repair_variation(self, plan: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        arrangement = []
        for index, section in enumerate(plan.get("arrangement") or []):
            updated = dict(section)
            updated["variation"] = int(updated.get("variation", index)) + attempt + 1

            if index % 2 == attempt % 2:
                current = float(updated.get("energy", 0.55))
                updated["energy"] = max(
                    0.15,
                    min(1.0, current + (0.09 if index % 3 else -0.08)),
                )
                updated["harmonic_motion"] = (
                    "contrast" if index % 3 == 0 else "lift"
                )

            arrangement.append(updated)

        plan["arrangement"] = arrangement

        dna = dict(plan.get("producer_dna") or {})
        dna["negative_space"] = min(
            1.0,
            float(dna.get("negative_space", 0.5)) + 0.05 * attempt,
        )
        dna["arrangement_density"] = max(
            0.15,
            float(dna.get("arrangement_density", 0.5)) - 0.04 * attempt,
        )
        plan["producer_dna"] = dna

        rhythm = dict(plan.get("rhythm_plan") or {})
        rhythm["variation_seed_offset"] = attempt
        rhythm["force_pattern_mutation"] = True
        plan["rhythm_plan"] = rhythm
        return plan
