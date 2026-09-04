import os
from typing import Dict, Any

from .procedural import ProceduralMusicProvider
from .providers import (
    MusicGenJascoProvider,
    RemoteWorkerProvider,
    StableAudioProvider,
)


class GenerationRouter:
    """Provider-agnostic generation layer."""

    def __init__(self):
        # Generate usable audio immediately even before an external GPU provider
        # is connected. A production AI model can replace this by environment var.
        self.provider = os.getenv("JUST_SOUNDZ_GENERATOR", "built-in-procedural")

    def generate(self, plan: Dict[str, Any], variation: int = 0):
        provider = self._build_provider()
        if provider is None:
            return {
                "provider": "unavailable",
                "audio_path": None,
                "message": f"Unknown or incomplete provider configuration: {self.provider}",
            }

        result = provider.generate(plan, variation)
        if not result.get("audio_path") and not result.get("audio_url"):
            result["message"] = "The configured worker returned no audio output."
        return result

    def _build_provider(self):
        if self.provider == "built-in-procedural":
            return ProceduralMusicProvider()

        url = os.getenv("JUST_SOUNDZ_WORKER_URL")
        if not url:
            return None

        token = os.getenv("JUST_SOUNDZ_WORKER_TOKEN")

        if self.provider == "http-worker":
            return RemoteWorkerProvider(url, token)
        if self.provider == "musicgen-jasco-worker":
            return MusicGenJascoProvider(url, token)
        if self.provider == "stable-audio-worker":
            return StableAudioProvider(url, token)

        return None
