from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import os
import tempfile
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

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def health(self, timeout_seconds: float = 2.5) -> Dict[str, Any]:
        import httpx

        timeout = max(0.25, min(float(timeout_seconds), 30.0))
        try:
            response = httpx.get(
                f"{self.base_url}/health",
                headers=self._headers(),
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            worker = payload.get("worker") if isinstance(payload, dict) else {}
            configured = (
                bool(worker.get("configured", True))
                if isinstance(worker, dict)
                else True
            )
            return {
                "ok": bool(payload.get("ok", True)) and configured,
                "configured": configured,
                "status_code": response.status_code,
            }
        except Exception as exc:
            return {
                "ok": False,
                "configured": False,
                "reason": exc.__class__.__name__,
            }

    def generate(self, plan: Dict[str, Any], variation: int = 0) -> Dict[str, Any]:
        import httpx

        headers = self._headers()
        payload = {
            "plan": plan,
            "conditioning": plan.get("conditioning") or {},
            "variation": variation,
        }
        generation_timeout = max(
            1.0,
            min(float(os.getenv("JUST_MAKER_WORKER_TIMEOUT_SECONDS", "600")), 1800.0),
        )
        response = httpx.post(
            f"{self.base_url}/generate",
            json=payload,
            headers=headers,
            timeout=generation_timeout,
        )
        response.raise_for_status()
        data = response.json()
        audio_path = data.get("audio_path")
        audio_url = data.get("audio_url")
        artifact_filename = data.get("artifact_filename")

        if not audio_path and not audio_url and artifact_filename:
            artifact_timeout = max(
                1.0,
                min(float(os.getenv("JUST_MAKER_ARTIFACT_TIMEOUT_SECONDS", "120")), 600.0),
            )
            artifact_response = httpx.get(
                f"{self.base_url}/artifacts/{artifact_filename}",
                headers=headers,
                timeout=artifact_timeout,
            )
            artifact_response.raise_for_status()
            suffix = Path(artifact_filename).suffix or ".wav"
            with tempfile.NamedTemporaryFile(
                prefix="just-maker-gpu-",
                suffix=suffix,
                delete=False,
            ) as f:
                f.write(artifact_response.content)
                audio_path = f.name

        return {
            "provider": data.get("provider", self.name),
            "audio_path": audio_path,
            "audio_url": audio_url,
            "metadata": data.get("metadata", {}),
            "worker": {
                "url": self.base_url,
                "status": "success",
                "artifact_filename": artifact_filename,
            },
        }


class MusicGenJascoProvider(RemoteWorkerProvider):
    """Adapter label for a MusicGen/JASCO-compatible worker."""

    name = "musicgen-jasco-worker"


class StableAudioProvider(RemoteWorkerProvider):
    """Adapter label for a Stable-Audio-compatible worker."""

    name = "stable-audio-worker"
