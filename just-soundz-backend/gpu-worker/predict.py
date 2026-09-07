from __future__ import annotations

import json
from pathlib import Path as FilePath
from typing import Any, Dict

from cog import BasePredictor, Input, Path

from worker import GPUWorker


class Predictor(BasePredictor):
    """Replicate/Cog entry point for the Just Maker GPU worker."""

    def setup(self) -> None:
        self.worker = GPUWorker()
        status = self.worker.status()
        if not status.get("model_configured"):
            raise RuntimeError(
                "JUST_MAKER_GPU_MODEL_ID must be configured for the Replicate deployment"
            )
        if not status.get("runtime_available"):
            raise RuntimeError(
                "GPU runtime dependencies are unavailable in the Cog image"
            )

    def predict(
        self,
        plan_json: str = Input(description="JSON-encoded Just Maker generation plan"),
        conditioning_json: str = Input(
            description="JSON-encoded structured Just Maker conditioning payload"
        ),
        variation: int = Input(
            description="Deterministic candidate variation index",
            default=0,
            ge=0,
            le=200,
        ),
    ) -> Path:
        plan = self._object(plan_json, "plan_json")
        conditioning = self._object(conditioning_json, "conditioning_json")

        result = self.worker.generate(
            plan=plan,
            conditioning=conditioning,
            variation=int(variation),
        )
        filename = result.get("artifact_filename")
        if not filename:
            raise RuntimeError("GPU worker did not return an audio artifact")

        path = FilePath(self.worker.output_dir) / FilePath(filename).name
        if not path.exists() or not path.is_file():
            raise RuntimeError("Generated audio artifact is missing")
        return Path(str(path))

    @staticmethod
    def _object(value: str, field: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field} must contain valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{field} must decode to an object")
        return parsed
