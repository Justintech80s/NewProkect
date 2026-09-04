from __future__ import annotations

from typing import Any, Dict


class ConditioningCompiler:
    """Compiles the rich Just Maker plan into a compact provider-neutral model payload."""

    def compile(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        dna = plan.get("producer_dna") or {}
        rhythm = plan.get("rhythm_plan") or {}
        harmony = plan.get("harmony_plan") or {}
        instruments = plan.get("instrumentation_plan") or {}
        samples = plan.get("sample_brain") or {}
        stems = plan.get("stem_arrangement") or {}

        return {
            "text": {
                "prompt": plan.get("original_prompt"),
                "negative": plan.get("negative_instructions") or [],
            },
            "musical": {
                "bpm": plan.get("bpm"),
                "key": plan.get("key"),
                "duration_seconds": plan.get("duration_seconds"),
                "harmony": harmony,
            },
            "rhythm": rhythm,
            "production": {
                "archetype": dna.get("archetype"),
                "swing": dna.get("swing"),
                "syncopation": dna.get("syncopation"),
                "negative_space": dna.get("negative_space"),
                "bass_prominence": dna.get("bass_prominence"),
                "sample_chop_intensity": dna.get("sample_chop_intensity"),
                "lofi_character": dna.get("lofi_character"),
                "mix_polish": dna.get("mix_polish"),
            },
            "instrumentation": instruments,
            "arrangement": plan.get("arrangement") or [],
            "stems": stems,
            "samples": {
                "processed": samples.get("processed_samples") or [],
                "policy": samples.get("policy"),
            },
            "music_brain": {
                "guidance": (plan.get("music_brain") or {}).get("guidance") or {},
                "reference_count": (plan.get("music_brain") or {}).get("reference_count", 0),
            },
            "advanced_controls": plan.get("advanced_conditioning") or {},
        }

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        enriched["conditioning"] = self.compile(enriched)
        return enriched
