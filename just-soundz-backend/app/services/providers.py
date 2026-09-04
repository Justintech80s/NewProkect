from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class MusicProvider(ABC):
    name = "base"

    @abstractmethod
    def generate(self, plan: Dict[str, Any], variation: int = 0) -> Dict[str, Any]:
        raise NotImplementedError


class RemoteWorkerProvider(MusicProvider):
    """Generic provider for a separately deployed GPU/music worker."""

    name = "http-worker"

    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def generate(self, plan: Dict[str, Any], variation: int = 0) -> Dict[str, Any]:
        import httpx

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        payload = {
            "plan": plan,
            "conditioning": plan.get("conditioning") or {},
            "variation": variation,
        }
        response = httpx.post(
            f"{self.base_url}/generate",
            json=payload,
            headers=headers,
            timeout=600,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "provider": data.get("provider", self.name),
            "audio_path": data.get("audio_path"),
            "audio_url": data.get("audio_url"),
            "metadata": data.get("metadata", {}),
            "worker": {
                "url": self.base_url,
                "status": "success",
            },
        }


class MusicGenJascoProvider(RemoteWorkerProvider):
    """Adapter label for a MusicGen/JASCO-compatible worker."""

    name = "musicgen-jasco-worker"


class StableAudioProvider(RemoteWorkerProvider):
    """Adapter label for a Stable-Audio-compatible worker."""

    name = "stable-audio-worker"
