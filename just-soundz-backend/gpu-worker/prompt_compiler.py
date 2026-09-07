from __future__ import annotations

from typing import Any, Dict, List


class ConditioningPromptCompiler:
    """Converts structured production intent into model-ready musical language."""

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
        reference = conditioning.get("reference") or {}
        style = conditioning.get("style_intent") or {}
        performance = conditioning.get("performance") or {}
        sampling = conditioning.get("sampling_intent") or {}
        novelty = conditioning.get("novelty") or {}

        parts: List[str] = []

        base_prompt = text.get("prompt") or plan.get("original_prompt")
        if base_prompt:
            parts.append(str(base_prompt))

        era = style.get("era")
        region = style.get("region")
        groove = style.get("groove_family")
        if era:
            parts.append(f"era target: {era} production language")
        if region:
            parts.append(f"regional production character: {str(region).replace('-', ' ')}")
        if groove:
            parts.append(
                f"groove target: {str(groove).replace('-', ' ')}, hard snare backbeat, swung pocket, phrase-level drum variation"
            )

        if performance.get("live_drums"):
            parts.append(
                "use a human-played acoustic drum kit feel: ghost notes, changing velocities, small timing offsets, fills at section boundaries, no rigid copy-paste loop"
            )
        if performance.get("live_bass"):
            parts.append(
                "use live electric bass guitar feel: note-length variation, slides, occasional approach notes, lock phrases to the kick while leaving breathing room"
            )
        if performance.get("humanization_required"):
            parts.append(
                "humanization is mandatory: microtiming, velocity variation, phrase-to-phrase changes and organic dynamics"
            )

        if sampling.get("requested"):
            parts.append(
                "sample-chop behavior: use only cleared, licensed or user-owned source material; short re-ordered chops, pitch variation, silence gaps, call-and-response edits and non-repeating chop sequences"
            )
            if sampling.get("avoid_loop_only_behavior"):
                parts.append(
                    "do not leave the source as a static repeated loop; transform the rhythm and ordering across sections"
                )

        stem_target = plan.get("stem_target")
        if stem_target:
            parts.append(
                f"generate isolated {stem_target} stem only, suitable for professional multitrack mixing"
            )

        bpm = musical.get("bpm") or plan.get("bpm")
        key = musical.get("key") or plan.get("key")
        if bpm:
            parts.append(f"lock tempo to {bpm} BPM")
        if key:
            parts.append(f"maintain tonal center {key}")

        archetype = production.get("archetype")
        if archetype:
            parts.append(f"production archetype {archetype.replace('_', ' ')}")

        swing = production.get("swing")
        syncopation = production.get("syncopation")
        negative_space = production.get("negative_space")
        chop = production.get("sample_chop_intensity")
        if swing is not None:
            parts.append(
                "rhythm feel: "
                + ("pronounced swung sixteenth-note pocket" if float(swing) >= 0.56 else "subtle swing and natural pocket")
            )
        if syncopation is not None and float(syncopation) >= 0.58:
            parts.append("use off-beat accents and syncopated phrase answers without overcrowding")
        if negative_space is not None and float(negative_space) >= 0.50:
            parts.append("leave deliberate negative space between musical phrases")
        if chop is not None and float(chop) >= 0.58:
            parts.append("make sample edits rhythmically active and section-dependent rather than static")

        primary = instruments.get("primary") or []
        if primary:
            parts.append("primary instruments: " + ", ".join(map(str, primary)))

        explicit = instruments.get("explicit_user_instruments") or []
        if explicit:
            parts.append("mandatory instrumentation: " + ", ".join(map(str, explicit)))

        progression = harmony.get("progression") or []
        if progression:
            parts.append("harmonic movement: " + "-".join(map(str, progression)))

        if rhythm.get("swing") is not None:
            parts.append(f"rhythmic swing control {float(rhythm['swing']):.2f}")
        if rhythm.get("percussion"):
            parts.append("use detailed syncopated percussion with changing accents")

        arrangement = conditioning.get("arrangement") or []
        if arrangement:
            summary = ", ".join(
                f"{s.get('section','section')} {s.get('bars','?')} bars"
                for s in arrangement[:8]
            )
            parts.append("arrangement: " + summary)
            parts.append(
                "each section must audibly differ through drum fills, instrument entry/exit, chop ordering, bass phrasing or energy"
            )

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
                "follow the planned kick, snare, hats, percussion, microtiming and humanized velocity pattern instead of substituting a generic stock groove"
            )

        concept = novelty.get("concept")
        if concept:
            parts.append(f"variation concept: {concept}")

        reference_traits = reference.get("production_traits") or {}
        if reference_traits:
            trait_summary = ", ".join(
                f"{name.replace('_', ' ')} {float(value):.2f}"
                for name, value in sorted(reference_traits.items())
            )
            parts.append(
                "match only these broad reference production traits: " + trait_summary
            )
            parts.append(
                "do not reproduce source melody, note sequence, lyrics or exact arrangement"
            )

        negative = list(text.get("negative") or [])
        anti_generic = [
            "generic preset-demo arrangement",
            "unchanged four-bar looping",
            "default modern trap hi-hat rolls when not requested",
            "random glossy EDM arpeggios",
            "mechanically quantized live-instrument feel",
        ]
        combined = []
        for item in negative + anti_generic:
            if item not in combined:
                combined.append(item)
        parts.append("avoid: " + ", ".join(map(str, combined[:16])))

        parts.append(f"variation pass {variation}")
        if stem_target:
            parts.append(f"exclude unrelated instruments from the {stem_target} stem")
        parts.append(
            "original instrumental composition; prioritize distinctive pocket, arrangement development and performance detail over generic genre shorthand"
        )

        return ". ".join(x for x in parts if x)
