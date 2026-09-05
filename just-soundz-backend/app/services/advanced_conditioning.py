from __future__ import annotations

from typing import Any, Dict, List


class AdvancedConditioningPlanner:
    """Turns the production plan into time-aligned control schedules.

    These controls are provider-neutral. Workers that support explicit control
    signals can consume them directly; text-only models still receive a compiled
    summary through the existing conditioning prompt.
    """

    def build(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        bpm = int(plan.get("bpm") or 90)
        beats_per_bar = 4
        seconds_per_beat = 60.0 / max(1, bpm)

        arrangement = list(plan.get("arrangement") or [])
        rhythm = plan.get("rhythm_plan") or {}
        harmony = plan.get("harmony_plan") or {}
        instrumentation = plan.get("instrumentation_plan") or {}
        dna = plan.get("producer_dna") or {}

        section_timeline = self._section_timeline(
            arrangement,
            seconds_per_beat,
            beats_per_bar,
        )
        chord_timeline = self._chord_timeline(
            harmony,
            section_timeline,
        )
        rhythm_controls = self._rhythm_controls(
            rhythm,
            seconds_per_beat,
        )
        instrument_controls = self._instrument_controls(
            instrumentation,
            section_timeline,
            float(dna.get("arrangement_density", 0.5)),
        )

        return {
            "tempo": {
                "bpm": bpm,
                "beats_per_bar": beats_per_bar,
                "seconds_per_beat": round(seconds_per_beat, 6),
                "tempo_lock": True,
            },
            "key": {
                "name": plan.get("key"),
                "tonic_emphasis": float(
                    (plan.get("harmony_plan") or {}).get("tonic_emphasis", 0.72)
                ),
            },
            "sections": section_timeline,
            "chords": chord_timeline,
            "rhythm": rhythm_controls,
            "instruments": instrument_controls,
            "production": {
                "swing": float(dna.get("swing", 0.52)),
                "syncopation": float(dna.get("syncopation", 0.5)),
                "negative_space": float(dna.get("negative_space", 0.5)),
                "bass_prominence": float(dna.get("bass_prominence", 0.75)),
                "mix_polish": float(dna.get("mix_polish", 0.8)),
                "brightness": float(dna.get("brightness", 0.5)),
                "transient_punch": float(dna.get("transient_punch", 0.5)),
                "dynamic_range": float(dna.get("dynamic_range", 0.5)),
            },
            "originality": {
                "direct_melodic_copying": False,
                "production_traits_only": True,
            },
        }

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        enriched["advanced_conditioning"] = self.build(enriched)
        return enriched

    def _section_timeline(
        self,
        arrangement: List[Dict[str, Any]],
        seconds_per_beat: float,
        beats_per_bar: int,
    ) -> List[Dict[str, Any]]:
        if not arrangement:
            arrangement = [
                {"section": "intro", "bars": 4, "energy": 0.35},
                {"section": "verse", "bars": 16, "energy": 0.58},
                {"section": "hook", "bars": 8, "energy": 0.88},
            ]

        out = []
        cursor = 0.0
        for index, section in enumerate(arrangement):
            bars = max(1, int(section.get("bars", 8)))
            duration = bars * beats_per_bar * seconds_per_beat
            out.append({
                "index": index,
                "section": str(section.get("section", f"section-{index}")),
                "bars": bars,
                "start_seconds": round(cursor, 4),
                "end_seconds": round(cursor + duration, 4),
                "energy": round(float(section.get("energy", 0.55)), 4),
                "variation": int(section.get("variation", index)),
            })
            cursor += duration
        return out

    def _chord_timeline(
        self,
        harmony: Dict[str, Any],
        sections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        progression = list(harmony.get("progression") or ["i", "VI", "III", "VII"])
        if not progression:
            return []

        out = []
        for section in sections:
            section_duration = max(
                0.01,
                float(section["end_seconds"]) - float(section["start_seconds"]),
            )
            chord_duration = section_duration / len(progression)
            for i, chord in enumerate(progression):
                start = float(section["start_seconds"]) + chord_duration * i
                out.append({
                    "section": section["section"],
                    "chord": str(chord),
                    "start_seconds": round(start, 4),
                    "end_seconds": round(start + chord_duration, 4),
                    "strength": round(
                        0.78 + min(0.18, 0.03 * section["energy"] * 10),
                        4,
                    ),
                })
        return out

    def _rhythm_controls(
        self,
        rhythm: Dict[str, Any],
        seconds_per_beat: float,
    ) -> Dict[str, Any]:
        step_seconds = seconds_per_beat / 4.0

        def events(name: str) -> List[Dict[str, Any]]:
            source = rhythm.get(name) or []
            if isinstance(source, dict):
                source = [
                    {"step": s, "velocity": 0.72}
                    for s in source.get("steps", [])
                ]
            out = []
            for item in source:
                if isinstance(item, int):
                    step = item
                    velocity = 0.72
                else:
                    step = int(item.get("step", 0))
                    velocity = float(item.get("velocity", 0.72))
                out.append({
                    "step": step,
                    "offset_seconds": round(step * step_seconds, 6),
                    "velocity": round(velocity, 4),
                })
            return out

        percussion = rhythm.get("percussion") or []
        return {
            "grid": rhythm.get("grid", "16-step"),
            "swing": float(rhythm.get("swing", 0.52)),
            "step_seconds": round(step_seconds, 6),
            "kick": events("kick"),
            "snare": events("snare"),
            "hats": events("hats"),
            "percussion": [
                {
                    "step": int(step),
                    "offset_seconds": round(int(step) * step_seconds, 6),
                    "velocity": 0.68,
                }
                for step in percussion
            ],
            "microtiming_ms": rhythm.get("microtiming_ms") or {},
            "humanization": rhythm.get("humanization") or {},
        }

    def _instrument_controls(
        self,
        instrumentation: Dict[str, Any],
        sections: List[Dict[str, Any]],
        density: float,
    ) -> List[Dict[str, Any]]:
        primary = list(instrumentation.get("primary") or [])
        secondary = list(instrumentation.get("secondary") or [])
        instruments = primary + secondary
        if not instruments:
            return []

        out = []
        for section in sections:
            energy = float(section.get("energy", 0.55))
            for index, name in enumerate(instruments):
                weight = (
                    0.88 - 0.08 * index
                    if index < len(primary)
                    else 0.48 - 0.04 * (index - len(primary))
                )
                weight *= 0.75 + 0.35 * energy
                weight *= 0.80 + 0.35 * density
                out.append({
                    "section": section["section"],
                    "instrument": str(name),
                    "weight": round(max(0.05, min(1.0, weight)), 4),
                    "start_seconds": section["start_seconds"],
                    "end_seconds": section["end_seconds"],
                })
        return out
