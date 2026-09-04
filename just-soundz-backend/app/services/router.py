import os
from typing import Dict, Any

from .providers import (
    MusicGenJascoProvider,
    RemoteWorkerProvider,
    StableAudioProvider,
)


class GenerationRouter:
    """Provider-agnostic generation layer."""

    def __init__(self):
        self.provider = os.getenv("JUST_SOUNDZ_GENERATOR", "disabled")

    def generate(self, plan: Dict[str, Any], variation: int = 0):
        provider = self._build_provider()
        if provider is None:
            return {
                "provider": "disabled",
                "audio_path": None,
                "message": (
                    "Generation architecture is installed, but no commercial or "
                    "approved music-model provider is configured yet."
                ),
            }

        result = provider.generate(plan, variation)
        if not result.get("audio_path") and not result.get("audio_url"):
            result["message"] = "The configured worker returned no audio output."
        return result

    def _build_provider(self):
        if self.provider == "disabled":
            return None

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
