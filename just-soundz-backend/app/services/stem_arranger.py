from __future__ import annotations

from typing import Any, Dict, List


class StemArranger:
    """Builds stem-level arrangement and mix instructions from the production plan."""

    STEM_ORDER = ["drums", "bass", "sample", "harmony", "lead", "texture", "fx"]

    def build(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        dna = plan.get("producer_dna") or {}
        inst = plan.get("instrumentation_plan") or {}
        arrangement = plan.get("arrangement") or []

        bass_prominence = float(dna.get("bass_prominence", 0.75))
        mix_polish = float(dna.get("mix_polish", 0.80))
        density = float(dna.get("arrangement_density", 0.50))
        lofi = float(dna.get("lofi_character", 0.20))

        stem_buses = {
            "drums": self._bus(-5.0, 0.0, 0.86 + 0.08 * mix_polish, "center"),
            "bass": self._bus(-7.5 + 2.5 * bass_prominence, 0.0, 0.80, "center"),
            "sample": self._bus(-9.0, -0.05, 0.68 + 0.12 * (1.0 - lofi), "wide"),
            "harmony": self._bus(-11.0, 0.10, 0.72, "wide"),
            "lead": self._bus(-10.0, -0.08, 0.76, "mid-wide"),
            "texture": self._bus(-16.0 + 3.0 * lofi, 0.15, 0.55, "wide"),
            "fx": self._bus(-18.0, -0.15, 0.50, "wide"),
        }

        section_map: List[Dict[str, Any]] = []
        for section in arrangement:
            name = str(section.get("section", "verse"))
            energy = float(section.get("energy", 0.55))
            active = self._active_stems(name, energy, density)
            section_map.append({
                "section": name,
                "bars": int(section.get("bars", 8)),
                "energy": energy,
                "active_stems": active,
                "dropout_candidates": self._dropouts(name, active),
            })

        return {
            "stems": stem_buses,
            "sections": section_map,
            "ducking": {
                "bass_from_kick_db": round(1.5 + 2.0 * bass_prominence, 2),
                "music_from_snare_db": round(0.5 + 1.0 * mix_polish, 2),
            },
            "stereo": {
                "keep_low_end_mono_hz": 130,
                "width_amount": round(0.55 + 0.30 * mix_polish, 3),
            },
            "instrumentation": inst,
        }

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        enriched["stem_arrangement"] = self.build(enriched)
        return enriched

    def _bus(self, gain_db: float, pan: float, compression: float, width: str) -> Dict[str, Any]:
        return {
            "gain_db": round(gain_db, 2),
            "pan": round(pan, 3),
            "compression_amount": round(max(0.0, min(1.0, compression)), 3),
            "stereo_width": width,
        }

    def _active_stems(self, section: str, energy: float, density: float) -> List[str]:
        active = ["drums", "bass"]
        if section not in {"intro", "outro"} or energy > 0.45:
            active.append("harmony")
        if density > 0.40 and section not in {"breakdown"}:
            active.append("sample")
        if energy > 0.70:
            active.append("lead")
        if section in {"intro", "bridge", "breakdown", "outro"}:
            active.append("texture")
        if energy > 0.85:
            active.append("fx")
        return [s for s in self.STEM_ORDER if s in active]

    def _dropouts(self, section: str, active: List[str]) -> List[str]:
        if section in {"hook", "prehook"}:
            return ["drums:1-beat", "bass:half-beat"]
        if section in {"bridge", "breakdown"}:
            return [f"{stem}:1-bar" for stem in active if stem not in {"texture"}][:2]
        return []
