from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
import os
import tempfile
import time
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


class ReplicateDeploymentProvider(MusicProvider):
    """Runs Just Maker's Cog model through a private Replicate deployment."""

    name = "replicate-deployment"

    def __init__(self, deployment: str, token: str | None):
        self.deployment = deployment.strip().strip("/")
        self.token = token

    def _headers(self, prefer_wait: bool = False) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if prefer_wait:
            headers["Prefer"] = "wait=60"
        return headers

    def _deployment_url(self) -> str:
        parts = [part for part in self.deployment.split("/") if part]
        if len(parts) != 2:
            raise RuntimeError(
                "JUST_SOUNDZ_REPLICATE_DEPLOYMENT must be owner/deployment-name"
            )
        owner, name = parts
        return f"https://api.replicate.com/v1/deployments/{owner}/{name}"

    def health(self, timeout_seconds: float = 2.5) -> Dict[str, Any]:
        import httpx

        if not self.token:
            return {
                "ok": False,
                "configured": False,
                "reason": "missing_replicate_token",
            }
        try:
            response = httpx.get(
                self._deployment_url(),
                headers=self._headers(),
                timeout=max(0.25, min(float(timeout_seconds), 30.0)),
            )
            response.raise_for_status()
            payload = response.json()
            release = payload.get("current_release") or {}
            return {
                "ok": bool(release),
                "configured": bool(release),
                "deployment": self.deployment,
                "hardware": (release.get("configuration") or {}).get("hardware"),
            }
        except Exception as exc:
            return {
                "ok": False,
                "configured": False,
                "reason": exc.__class__.__name__,
            }

    def generate(self, plan: Dict[str, Any], variation: int = 0) -> Dict[str, Any]:
        import httpx

        if not self.token:
            raise RuntimeError("JUST_SOUNDZ_REPLICATE_API_TOKEN is not configured")

        timeout_seconds = max(
            30.0,
            min(float(os.getenv("JUST_MAKER_REPLICATE_TIMEOUT_SECONDS", "900")), 1800.0),
        )
        create = httpx.post(
            f"{self._deployment_url()}/predictions",
            headers=self._headers(prefer_wait=True),
            json={
                "input": {
                    "plan_json": json.dumps(plan, separators=(",", ":")),
                    "conditioning_json": json.dumps(
                        plan.get("conditioning") or {},
                        separators=(",", ":"),
                    ),
                    "variation": int(variation),
                }
            },
            timeout=70.0,
        )
        create.raise_for_status()
        prediction = create.json()
        prediction = self._wait(prediction, timeout_seconds=timeout_seconds)

        if prediction.get("status") != "succeeded":
            raise RuntimeError(
                f"Replicate prediction failed: {prediction.get('error') or prediction.get('status')}"
            )

        output = prediction.get("output")
        audio_url = self._output_url(output)
        if not audio_url:
            raise RuntimeError("Replicate prediction returned no audio file")

        artifact = httpx.get(
            audio_url,
            headers=self._headers(),
            timeout=max(
                30.0,
                min(float(os.getenv("JUST_MAKER_ARTIFACT_TIMEOUT_SECONDS", "120")), 600.0),
            ),
        )
        artifact.raise_for_status()
        suffix = Path(audio_url.split("?", 1)[0]).suffix or ".wav"
        with tempfile.NamedTemporaryFile(
            prefix="just-maker-replicate-",
            suffix=suffix,
            delete=False,
        ) as f:
            f.write(artifact.content)
            audio_path = f.name

        return {
            "provider": self.name,
            "audio_path": audio_path,
            "audio_url": None,
            "metadata": {
                "prediction_id": prediction.get("id"),
                "deployment": self.deployment,
                "metrics": prediction.get("metrics") or {},
                "replicate_web_url": (prediction.get("urls") or {}).get("web"),
            },
            "worker": {
                "deployment": self.deployment,
                "status": "success",
            },
        }

    def _wait(self, prediction: Dict[str, Any], timeout_seconds: float) -> Dict[str, Any]:
        import httpx

        started = time.time()
        terminal = {"succeeded", "failed", "canceled"}
        while prediction.get("status") not in terminal:
            if time.time() - started >= timeout_seconds:
                raise TimeoutError("Replicate prediction timed out")
            get_url = (prediction.get("urls") or {}).get("get")
            if not get_url:
                raise RuntimeError("Replicate prediction did not provide polling URL")
            time.sleep(1.5)
            response = httpx.get(
                get_url,
                headers=self._headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            prediction = response.json()
        return prediction

    @staticmethod
    def _output_url(output: Any) -> str | None:
        if isinstance(output, str):
            return output
        if isinstance(output, list):
            for item in output:
                if isinstance(item, str):
                    return item
        if isinstance(output, dict):
            for key in ("audio", "audio_url", "file", "output"):
                value = output.get(key)
                if isinstance(value, str):
                    return value
        return None


class MusicGenJascoProvider(RemoteWorkerProvider):
    """Adapter label for a MusicGen/JASCO-compatible worker."""

    name = "musicgen-jasco-worker"


class StableAudioProvider(RemoteWorkerProvider):
    """Adapter label for a Stable-Audio-compatible worker."""

    name = "stable-audio-worker"
