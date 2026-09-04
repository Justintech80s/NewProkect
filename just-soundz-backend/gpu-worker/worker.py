from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any, Dict

from prompt_compiler import ConditioningPromptCompiler


class GPUWorker:
    """GPU-backed music generation service.

    The model is selected entirely by environment configuration so production
    can use only model weights whose license is appropriate for the deployment.
    """

    def __init__(self):
        self.backend = os.getenv("JUST_MAKER_GPU_BACKEND", "transformers-musicgen")
        self.model_id = os.getenv("JUST_MAKER_GPU_MODEL_ID", "")
        self.device = os.getenv("JUST_MAKER_GPU_DEVICE", "cuda")
        self.max_seconds = int(os.getenv("JUST_MAKER_GPU_MAX_SECONDS", "180"))
        self.output_dir = Path(os.getenv("JUST_MAKER_GPU_OUTPUT_DIR", "/tmp/just-maker-gpu"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.compiler = ConditioningPromptCompiler()
        self._adapter = None

    def status(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "model_id": self.model_id or None,
            "device": self.device,
            "configured": bool(self.model_id),
            "loaded": self._adapter is not None,
            "max_seconds": self.max_seconds,
        }

    def capabilities(self) -> Dict[str, Any]:
        return {
            "text_prompt": True,
            "bpm": True,
            "key": True,
            "rhythm_conditioning": True,
            "harmony_conditioning": True,
            "instrumentation_conditioning": True,
            "arrangement_conditioning": True,
            "stem_conditioning": False,
            "sample_conditioning": False,
            "negative_prompt": True,
            "max_duration_seconds": self.max_seconds,
            "conditioning_mode": "compiled-text-plus-generation-controls",
        }

    def generate(
        self,
        plan: Dict[str, Any],
        conditioning: Dict[str, Any],
        variation: int = 0,
    ) -> Dict[str, Any]:
        if not self.model_id:
            raise RuntimeError("JUST_MAKER_GPU_MODEL_ID is not configured")

        duration = min(
            int(plan.get("duration_seconds") or 120),
            self.max_seconds,
        )
        prompt = self.compiler.compile(plan, conditioning, variation)
        adapter = self._get_adapter()

        started = time.time()
        audio, sample_rate, metadata = adapter.generate(
            prompt=prompt,
            duration_seconds=duration,
            variation=variation,
        )

        digest = hashlib.sha256(
            f"{prompt}|{variation}|{time.time_ns()}".encode("utf-8")
        ).hexdigest()[:16]
        filename = f"just-maker-{digest}.wav"
        path = self.output_dir / filename
        adapter.write_wav(path, audio, sample_rate)

        return {
            "provider": f"gpu:{self.backend}",
            "audio_path": str(path),
            "audio_url": None,
            "metadata": {
                **metadata,
                "model_id": self.model_id,
                "duration_seconds": duration,
                "elapsed_seconds": round(time.time() - started, 3),
                "conditioning_prompt": prompt,
                "variation": variation,
            },
        }

    def _get_adapter(self):
        if self._adapter is not None:
            return self._adapter

        if self.backend == "transformers-musicgen":
            from adapters.musicgen_transformers import TransformersMusicGenAdapter
            self._adapter = TransformersMusicGenAdapter(
                model_id=self.model_id,
                device=self.device,
            )
            return self._adapter

        raise RuntimeError(f"Unsupported GPU backend: {self.backend}")
