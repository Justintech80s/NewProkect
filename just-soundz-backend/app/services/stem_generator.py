from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


class ProfessionalStemGenerator:
    """Builds separate generation requests for production stems before final mixdown."""

    STEMS = ["drums", "bass", "harmony", "lead", "texture", "fx"]

    def build_requests(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        stem_arrangement = plan.get("stem_arrangement") or {}
        buses = stem_arrangement.get("stems") or {}
        instrumentation = plan.get("instrumentation_plan") or {}
        primary = list(instrumentation.get("primary") or [])
        secondary = list(instrumentation.get("secondary") or [])

        requests: List[Dict[str, Any]] = []
        for stem in self.STEMS:
            if stem not in buses:
                continue

            stem_plan = deepcopy(plan)
            stem_plan["stem_target"] = stem
            stem_plan["stem_generation"] = True
            stem_plan["negative_instructions"] = list(
                stem_plan.get("negative_instructions") or []
            ) + self._negative_for(stem)
            stem_plan["instrumentation_plan"] = {
                "primary": self._instruments_for(stem, primary, secondary),
                "secondary": [],
            }
            stem_plan["stem_arrangement"] = {
                "stems": {stem: buses[stem]},
                "sections": stem_arrangement.get("sections") or [],
                "ducking": stem_arrangement.get("ducking") or {},
                "stereo": stem_arrangement.get("stereo") or {},
            }
            requests.append({
                "stem": stem,
                "plan": stem_plan,
                "bus": buses[stem],
            })

        return requests

    def _negative_for(self, stem: str) -> List[str]:
        exclusions = {
            "drums": ["no bass line", "no melody", "no chords", "no vocals"],
            "bass": ["no drums", "no lead melody", "no vocals"],
            "harmony": ["no drums", "no bass", "no lead melody", "no vocals"],
            "lead": ["no drums", "no bass", "no chord pad", "no vocals"],
            "texture": ["no drums", "no bass", "no lead melody", "no vocals"],
            "fx": ["no drum groove", "no bass line", "no melody", "no vocals"],
        }
        return exclusions.get(stem, [])

    def _instruments_for(
        self,
        stem: str,
        primary: List[str],
        secondary: List[str],
    ) -> List[str]:
        source = primary + secondary
        keywords = {
            "drums": ("drum", "kick", "snare", "hat", "percussion"),
            "bass": ("bass", "sub"),
            "harmony": ("piano", "keys", "rhodes", "string", "pad", "guitar", "chord"),
            "lead": ("lead", "synth", "melody", "horn"),
            "texture": ("texture", "ambient", "noise", "sample"),
            "fx": ("fx", "effect", "risers", "impact"),
        }
        matched = [
            item for item in source
            if any(k in item.lower() for k in keywords.get(stem, ()))
        ]
        return matched or [stem]
