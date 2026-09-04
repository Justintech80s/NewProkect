import re
from typing import Optional

class ProducerPlanner:
    """Turns a loose user prompt into structured production instructions."""

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
            "drums": self._drum_profile(p),
            "harmony": self._harmony_profile(p),
            "bass": self._bass_profile(p),
            "arrangement": self.DEFAULT_ARRANGEMENT,
            "vocals": "none" if "no vocal" in p or "instrumental" in p else "optional",
            "negative_instructions": ["avoid clipping", "avoid abrupt cutoffs", "maintain musical continuity"],
        }

    def _infer_bpm(self, prompt: str) -> int:
        m = re.search(r"\b(\d{2,3})\s*bpm\b", prompt)
        if m:
            return max(40, min(240, int(m.group(1))))
        if any(x in prompt for x in ["trap", "drill"]):
            return 140
        if any(x in prompt for x in ["boom bap", "90s hip hop"]):
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

    def _drum_profile(self, prompt):
        return {
            "feel": "syncopated" if any(x in prompt for x in ["bounce", "syncopated", "timbaland"]) else "steady",
            "texture": "dusty" if any(x in prompt for x in ["dusty", "90s", "boom bap"]) else "clean",
            "density": "sparse" if "sparse" in prompt else "medium",
        }

    def _harmony_profile(self, prompt):
        return {
            "complexity": "extended" if any(x in prompt for x in ["jazz", "neo soul", "soul"]) else "modern",
            "voicings": ["minor 7", "add9"] if any(x in prompt for x in ["dark", "soul", "moody"]) else ["triads", "sus2"],
        }

    def _bass_profile(self, prompt):
        return {
            "type": "808" if "808" in prompt or "trap" in prompt else "synth bass",
            "movement": "minimal" if "sparse" in prompt else "supportive",
        }
