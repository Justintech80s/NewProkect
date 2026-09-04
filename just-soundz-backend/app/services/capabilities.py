from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List


@dataclass
class WorkerCapabilities:
    text_prompt: bool = True
    bpm: bool = False
    key: bool = False
    rhythm_conditioning: bool = False
    harmony_conditioning: bool = False
    instrumentation_conditioning: bool = False
    arrangement_conditioning: bool = False
    stem_conditioning: bool = False
    sample_conditioning: bool = False
    negative_prompt: bool = False
    max_duration_seconds: int = 120

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def coverage(self, required: Iterable[str]) -> float:
        required = list(required)
        if not required:
            return 1.0
        supported = 0
        for name in required:
            if bool(getattr(self, name, False)):
                supported += 1
        return supported / len(required)


class CapabilityRequirements:
    """Infers which conditioning capabilities a Just Maker plan actually needs."""

    def required(self, plan: Dict[str, Any]) -> List[str]:
        required = ["text_prompt"]
        conditioning = plan.get("conditioning") or {}
        musical = conditioning.get("musical") or {}

        if musical.get("bpm") is not None:
            required.append("bpm")
        if musical.get("key"):
            required.append("key")
        if conditioning.get("rhythm"):
            required.append("rhythm_conditioning")
        if (musical.get("harmony") or {}):
            required.append("harmony_conditioning")
        if conditioning.get("instrumentation"):
            required.append("instrumentation_conditioning")
        if conditioning.get("arrangement"):
            required.append("arrangement_conditioning")
        if conditioning.get("stems"):
            required.append("stem_conditioning")
        if ((conditioning.get("samples") or {}).get("processed")):
            required.append("sample_conditioning")
        if ((conditioning.get("text") or {}).get("negative")):
            required.append("negative_prompt")
        return required
