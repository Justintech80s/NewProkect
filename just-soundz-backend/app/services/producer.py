import re
from typing import Optional


class ProducerPlanner:
    """Turns a loose user prompt into structured, audible production instructions."""

    DEFAULT_ARRANGEMENT = [
        {"section": "intro", "bars": 8},
        {"section": "verse", "bars": 16},
        {"section": "hook", "bars": 8},
        {"section": "verse", "bars": 16},
        {"section": "breakdown", "bars": 8},
        {"section": "hook", "bars": 8},
        {"section": "outro", "bars": 8},
    ]

    def build_plan(self, prompt: str, bpm: Optional[int], key: Optional[str], duration_seconds: int):
        p = prompt.lower()
        inferred_bpm = bpm or self._infer_bpm(p)
        inferred_key = key or self._infer_key(p)

        return {
            "original_prompt": prompt,
            "duration_seconds": duration_seconds,
            "bpm": inferred_bpm,
            "key": inferred_key,
            "mood": self._tags(p, {
                "dark": ["dark", "eerie", "ominous"],
                "uplifting": ["bright", "uplifting", "happy"],
                "aggressive": ["hard", "aggressive", "menacing"],
                "dreamy": ["dreamy", "ambient", "ethereal"],
            }),
            "style_intent": self._style_intent(p),
            "performance": self._performance_profile(p),
            "sampling": self._sampling_profile(p),
            "drums": self._drum_profile(p),
            "harmony": self._harmony_profile(p),
            "bass": self._bass_profile(p),
            "arrangement": self.DEFAULT_ARRANGEMENT,
            "vocals": "none" if "no vocal" in p or "instrumental" in p else "optional",
            "negative_instructions": self._negative_instructions(p),
        }

    def _infer_bpm(self, prompt: str) -> int:
        m = re.search(r"\b(\d{2,3})\s*bpm\b", prompt)
        if m:
            return max(40, min(240, int(m.group(1))))
        if any(x in prompt for x in ["trap", "drill"]):
            return 140
        if any(x in prompt for x in ["boom bap", "90s hip hop", "90s sounding hip hop", "east coast"]):
            return 92
        if any(x in prompt for x in ["house", "club", "dance"]):
            return 124
        return 100

    def _infer_key(self, prompt: str) -> str:
        keys = ["c", "c#", "db", "d", "d#", "eb", "e", "f", "f#", "gb", "g", "g#", "ab", "a", "a#", "bb", "b"]
        for k in keys:
            if f"{k} minor" in prompt:
                return f"{k.upper()} minor"
            if f"{k} major" in prompt:
                return f"{k.upper()} major"
        return "F# minor" if any(x in prompt for x in ["dark", "eerie", "menacing"]) else "C minor"

    def _tags(self, prompt, mapping):
        out = []
        for label, words in mapping.items():
            if any(w in prompt for w in words):
                out.append(label)
        return out or ["focused"]

    def _style_intent(self, prompt: str):
        era = "1990s" if any(x in prompt for x in ["90s", "1990s"]) else None
        region = "east-coast-us" if "east coast" in prompt else None
        groove = "boom-bap" if any(x in prompt for x in ["boom bap", "90s hip hop", "east coast"]) else None
        return {
            "era": era,
            "region": region,
            "groove_family": groove,
            "organic_feel": any(x in prompt for x in ["live drums", "live bass", "live band", "organic"]),
            "specificity": "high" if any([era, region, groove]) else "standard",
        }

    def _performance_profile(self, prompt: str):
        live_drums = any(x in prompt for x in ["live drums", "live drum", "acoustic drums"])
        live_bass = any(x in prompt for x in ["live bass", "electric bass", "bass guitar"])
        return {
            "live_drums": live_drums,
            "live_bass": live_bass,
            "drum_execution": (
                "human-played acoustic kit with ghost notes, velocity variation and microtiming"
                if live_drums else "programmed with deliberate velocity and timing variation"
            ),
            "bass_execution": (
                "human-played electric bass with note-length variation, slides and pocket interaction"
                if live_bass else "supportive bass line with phrase-level variation"
            ),
            "humanization_required": live_drums or live_bass or "90s" in prompt or "east coast" in prompt,
        }

    def _sampling_profile(self, prompt: str):
        requested = any(x in prompt for x in ["sample", "chop", "chops", "sampling"])
        return {
            "requested": requested,
            "technique": (
                "short re-ordered chops with pitch variation, silence gaps and call-and-response"
                if requested else "none"
            ),
            "chop_density": "medium-high" if any(x in prompt for x in ["sample chops", "chopped sample", "chops"]) else "medium",
            "source_policy": "cleared-user-owned-or-licensed-only",
            "avoid_loop_only_behavior": requested,
        }

    def _drum_profile(self, prompt):
        boom_bap = any(x in prompt for x in ["boom bap", "90s hip hop", "east coast", "90s sounding hip hop"])
        return {
            "feel": "swung boom-bap pocket" if boom_bap else (
                "syncopated" if any(x in prompt for x in ["bounce", "syncopated"]) else "steady"
            ),
            "texture": "dusty" if any(x in prompt for x in ["dusty", "90s", "boom bap", "east coast"]) else "clean",
            "density": "sparse" if "sparse" in prompt else "medium",
            "humanized": boom_bap or "live drums" in prompt,
            "ghost_notes": bool("live drums" in prompt or boom_bap),
        }

    def _harmony_profile(self, prompt):
        return {
            "complexity": "extended" if any(x in prompt for x in ["jazz", "neo soul", "soul"]) else "modern",
            "voicings": ["minor 7", "add9"] if any(x in prompt for x in ["dark", "soul", "moody"]) else ["triads", "sus2"],
        }

    def _bass_profile(self, prompt):
        if any(x in prompt for x in ["live bass", "electric bass", "bass guitar"]):
            bass_type = "live electric bass"
        elif "808" in prompt or "trap" in prompt:
            bass_type = "808"
        else:
            bass_type = "synth bass"
        return {
            "type": bass_type,
            "movement": "minimal" if "sparse" in prompt else "supportive",
            "lock_to_kick": True,
        }

    def _negative_instructions(self, prompt: str):
        negatives = [
            "avoid clipping",
            "avoid abrupt cutoffs",
            "maintain musical continuity",
            "avoid repetitive four-bar copy-paste behavior",
            "avoid generic preset-demo arrangement",
        ]
        if any(x in prompt for x in ["90s", "east coast", "boom bap"]):
            negatives.extend([
                "avoid modern trap hi-hat rolls unless explicitly requested",
                "avoid glossy EDM synth arpeggios",
                "avoid oversized modern festival-style drops",
            ])
        return negatives
