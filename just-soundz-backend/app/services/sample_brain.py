from __future__ import annotations

from typing import Any, Dict, List


class SampleBrain:
    """Selects and plans transformations for rights-cleared sample candidates only."""

    def prepare(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        music_brain = plan.get("music_brain") or {}
        candidates = music_brain.get("eligible_samples") or []
        target_bpm = plan.get("bpm")
        target_key = plan.get("key")

        ranked: List[Dict[str, Any]] = []
        for candidate in candidates:
            if not candidate.get("sampling_allowed"):
                continue
            score = float(candidate.get("similarity") or 0.0)
            bpm = candidate.get("bpm")
            if bpm and target_bpm:
                delta = abs(float(bpm) - float(target_bpm))
                score += max(0.0, 0.15 - min(delta, 30.0) / 200.0)
            if candidate.get("key") and target_key and candidate["key"] == target_key:
                score += 0.10

            ranked.append({
                **candidate,
                "sample_score": round(score, 4),
                "transform": self._transform(candidate, target_bpm, target_key),
            })

        ranked.sort(key=lambda row: row["sample_score"], reverse=True)
        selected = ranked[:4]

        return {
            "policy": "rights-cleared-only",
            "candidate_count": len(candidates),
            "eligible_count": len(ranked),
            "selected": selected,
            "instructions": [
                "use only sampling_allowed assets",
                "preserve source provenance",
                "never substitute reference-only recordings as audio",
            ],
        }

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        enriched["sample_brain"] = self.prepare(enriched)
        return enriched

    def _transform(self, candidate: Dict[str, Any], target_bpm: Any, target_key: Any) -> Dict[str, Any]:
        source_bpm = candidate.get("bpm")
        ratio = None
        if source_bpm and target_bpm:
            ratio = round(float(target_bpm) / float(source_bpm), 5)

        return {
            "target_bpm": target_bpm,
            "target_key": target_key,
            "time_stretch_ratio": ratio,
            "pitch_strategy": "key-match" if candidate.get("key") and target_key else "preserve",
            "chop_strategy": "transient-aware",
            "variation": ["slice", "reorder", "filter", "reverse-accent"],
        }
