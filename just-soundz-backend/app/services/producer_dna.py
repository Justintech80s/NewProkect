from __future__ import annotations

from typing import Any, Dict


class ProducerDNAEngine:
    """Converts production intent into measurable, original production controls.

    The engine uses broad production archetypes rather than attempting to clone
    any individual living producer's exact signature.
    """

    ARCHETYPES = {
        "polished_west_coast": {
            "swing": 0.54,
            "syncopation": 0.42,
            "negative_space": 0.55,
            "kick_density": 0.34,
            "snare_density": 0.18,
            "percussion_complexity": 0.36,
            "bass_prominence": 0.88,
            "harmonic_complexity": 0.46,
            "sample_chop_intensity": 0.28,
            "arrangement_density": 0.58,
            "lofi_character": 0.12,
            "mix_polish": 0.92,
        },
        "syncopated_futurist": {
            "swing": 0.59,
            "syncopation": 0.88,
            "negative_space": 0.76,
            "kick_density": 0.29,
            "snare_density": 0.17,
            "percussion_complexity": 0.90,
            "bass_prominence": 0.72,
            "harmonic_complexity": 0.40,
            "sample_chop_intensity": 0.48,
            "arrangement_density": 0.44,
            "lofi_character": 0.16,
            "mix_polish": 0.82,
        },
        "gritty_cinematic_sampler": {
            "swing": 0.57,
            "syncopation": 0.63,
            "negative_space": 0.61,
            "kick_density": 0.38,
            "snare_density": 0.20,
            "percussion_complexity": 0.47,
            "bass_prominence": 0.66,
            "harmonic_complexity": 0.52,
            "sample_chop_intensity": 0.90,
            "arrangement_density": 0.50,
            "lofi_character": 0.86,
            "mix_polish": 0.46,
        },
        "soul_chop_maximalist": {
            "swing": 0.56,
            "syncopation": 0.58,
            "negative_space": 0.42,
            "kick_density": 0.37,
            "snare_density": 0.19,
            "percussion_complexity": 0.55,
            "bass_prominence": 0.73,
            "harmonic_complexity": 0.78,
            "sample_chop_intensity": 0.82,
            "arrangement_density": 0.72,
            "lofi_character": 0.42,
            "mix_polish": 0.84,
            "vocal_texture": 0.72,
            "gospel_color": 0.68,
            "orchestral_layering": 0.52,
        },
        "electro_minimalist": {
            "swing": 0.50,
            "syncopation": 0.62,
            "negative_space": 0.80,
            "kick_density": 0.31,
            "snare_density": 0.16,
            "percussion_complexity": 0.64,
            "bass_prominence": 0.80,
            "harmonic_complexity": 0.36,
            "sample_chop_intensity": 0.20,
            "arrangement_density": 0.40,
            "lofi_character": 0.10,
            "mix_polish": 0.91,
            "vocal_texture": 0.35,
            "gospel_color": 0.08,
            "orchestral_layering": 0.12,
        },
        "modern_minimal": {
            "swing": 0.51,
            "syncopation": 0.56,
            "negative_space": 0.81,
            "kick_density": 0.28,
            "snare_density": 0.17,
            "percussion_complexity": 0.55,
            "bass_prominence": 0.84,
            "harmonic_complexity": 0.34,
            "sample_chop_intensity": 0.32,
            "arrangement_density": 0.39,
            "lofi_character": 0.18,
            "mix_polish": 0.87,
        },
    }

    def build_profile(self, prompt: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        archetype = self._select_archetype(prompt)
        profile = dict(self.ARCHETYPES[archetype])

        # Blend Music Brain evidence into broad controls where available.
        context = plan.get("production_context") or {}
        genres = {str(x).lower() for x in context.get("genres") or []}
        moods = {str(x).lower() for x in context.get("moods") or []}

        if {"soul", "funk"} & genres:
            profile["harmonic_complexity"] = min(1.0, profile["harmonic_complexity"] + 0.10)
        if {"dark", "ominous", "gritty"} & moods:
            profile["lofi_character"] = min(1.0, profile["lofi_character"] + 0.08)
            profile["negative_space"] = min(1.0, profile["negative_space"] + 0.05)

        profile["archetype"] = archetype
        profile["bpm"] = plan.get("bpm")
        profile["key"] = plan.get("key")
        profile["originality_policy"] = "broad-production-traits-only"
        profile["identity_policy"] = {
            "artist_voice_clone": False,
            "melody_copy": False,
            "recording_copy": False,
            "copyrighted_sample_auto_use": False,
            "named_reference_translated_to_traits": True,
        }
        return profile

    def apply(self, prompt: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        enriched["producer_dna"] = self.build_profile(prompt, enriched)
        return enriched

    def _select_archetype(self, prompt: str) -> str:
        p = prompt.lower()

        # Named artist/producer references are translated into broad musical
        # characteristics rather than direct identity/style cloning.
        if any(term in p for term in [
            "kanye", "chipmunk soul", "soul sample", "pitched soul",
            "gospel hip hop", "maximalist hip hop", "orchestral hip hop"
        ]):
            if any(term in p for term in [
                "yeezus", "industrial", "electronic minimal", "abrasive synth"
            ]):
                return "electro_minimalist"
            return "soul_chop_maximalist"

        if any(term in p for term in [
            "west coast", "g-funk", "polished drums", "synth bass", "clean hip hop"
        ]):
            return "polished_west_coast"

        if any(term in p for term in [
            "syncopated", "futuristic percussion", "weird drums",
            "unusual percussion", "off-grid", "negative space"
        ]):
            return "syncopated_futurist"

        if any(term in p for term in [
            "gritty", "dusty", "cinematic sample", "chopped soul",
            "lo-fi hip hop", "raw sample"
        ]):
            return "gritty_cinematic_sampler"

        return "modern_minimal"
