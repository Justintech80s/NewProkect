from __future__ import annotations

from typing import Any, Dict


class SectionRepairEngine:
    """Adjusts the production plan when the rendered track is too repetitive."""

    def repair_plan(self, plan: Dict[str, Any], repetition: Dict[str, object], attempt: int) -> Dict[str, Any]:
        repaired = dict(plan)
        repaired["repair_attempt"] = attempt

        arrangement = []
        for idx, section in enumerate(plan.get("arrangement", [])):
            updated = dict(section)
            if idx % 2 == attempt % 2:
                updated["variation"] = int(updated.get("variation", idx)) + attempt + 1
                updated["energy"] = max(
                    0.15,
                    min(1.0, float(updated.get("energy", 0.55)) + (0.06 if idx % 3 else -0.05))
                )
                updated["harmonic_motion"] = "contrast" if idx % 3 == 0 else "lift"
            arrangement.append(updated)

        repaired["arrangement"] = arrangement

        drums = dict(plan.get("drums", {}))
        drums["density"] = "medium" if drums.get("density") == "sparse" else "sparse"
        repaired["drums"] = drums

        repaired["repair_reason"] = {
            "type": "excessive_repetition",
            "score": repetition.get("score"),
        }
        return repaired
