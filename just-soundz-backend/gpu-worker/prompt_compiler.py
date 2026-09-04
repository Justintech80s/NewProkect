from __future__ import annotations

from typing import Any, Dict, List


class ConditioningPromptCompiler:
    """Converts Just Maker's structured production plan into model-ready language."""

    def compile(
        self,
        plan: Dict[str, Any],
        conditioning: Dict[str, Any],
        variation: int,
    ) -> str:
        text = conditioning.get("text") or {}
        musical = conditioning.get("musical") or {}
        production = conditioning.get("production") or {}
        instruments = conditioning.get("instrumentation") or {}
        rhythm = conditioning.get("rhythm") or {}
        harmony = musical.get("harmony") or {}
        advanced = conditioning.get("advanced_controls") or {}

        parts: List[str] = []

        base_prompt = text.get("prompt") or plan.get("original_prompt")
        if base_prompt:
            parts.append(str(base_prompt))

        bpm = musical.get("bpm") or plan.get("bpm")
        key = musical.get("key") or plan.get("key")
        if bpm:
            parts.append(f"tempo {bpm} BPM")
        if key:
            parts.append(f"key {key}")

        archetype = production.get("archetype")
        if archetype:
            parts.append(f"production archetype {archetype.replace('_', ' ')}")

        for label, value in [
            ("swing", production.get("swing")),
            ("syncopation", production.get("syncopation")),
            ("negative space", production.get("negative_space")),
            ("bass prominence", production.get("bass_prominence")),
            ("sample chop intensity", production.get("sample_chop_intensity")),
            ("lofi character", production.get("lofi_character")),
            ("mix polish", production.get("mix_polish")),
        ]:
            if value is not None:
                parts.append(f"{label} {float(value):.2f}")

        primary = instruments.get("primary") or []
        if primary:
            parts.append("primary instruments: " + ", ".join(map(str, primary)))

        progression = harmony.get("progression") or []
        if progression:
            parts.append("harmonic movement: " + "-".join(map(str, progression)))

        if rhythm.get("swing") is not None:
            parts.append(f"rhythmic swing {float(rhythm['swing']):.2f}")
        if rhythm.get("percussion"):
            parts.append("detailed syncopated percussion")

        arrangement = conditioning.get("arrangement") or []
        if arrangement:
            summary = ", ".join(
                f"{s.get('section','section')} {s.get('bars','?')} bars"
                for s in arrangement[:8]
            )
            parts.append("arrangement: " + summary)

        sections = advanced.get("sections") or []
        if sections:
            section_energy = ", ".join(
                f"{s.get('section','section')} energy {float(s.get('energy',0.5)):.2f}"
                for s in sections[:8]
            )
            parts.append("section energy map: " + section_energy)

        chord_controls = advanced.get("chords") or []
        if chord_controls:
            chord_summary = ", ".join(
                f"{c.get('chord')} at {float(c.get('start_seconds',0)):.1f}s"
                for c in chord_controls[:12]
            )
            parts.append("timed chord controls: " + chord_summary)

        rhythm_controls = advanced.get("rhythm") or {}
        if rhythm_controls:
            parts.append(
                "locked 16-step rhythmic control with kick, snare, hats, percussion, "
                "microtiming and humanized velocity"
            )

        negative = text.get("negative") or []
        if negative:
            parts.append("avoid: " + ", ".join(map(str, negative[:12])))

        parts.append(f"variation pass {variation}")
        parts.append("original instrumental composition, no direct melodic copying")

        return ". ".join(x for x in parts if x)
