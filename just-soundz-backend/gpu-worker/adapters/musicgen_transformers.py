from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np


class TransformersMusicGenAdapter:
    """CUDA adapter for MusicGen-compatible Hugging Face models.

    The deployment chooses the model ID. Just Maker does not hard-code weights,
    so the operator can select only models whose license fits the intended use.
    """

    def __init__(self, model_id: str, device: str = "cuda"):
        self.model_id = model_id
        self.device = device
        self.processor = None
        self.model = None

    def load(self):
        if self.model is not None:
            return

        import torch
        from transformers import AutoProcessor, MusicgenForConditionalGeneration

        if self.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but no CUDA device is available")

        dtype = torch.float16 if self.device.startswith("cuda") else torch.float32
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = MusicgenForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
        ).to(self.device)
        self.model.eval()

    def generate(
        self,
        prompt: str,
        duration_seconds: int,
        variation: int,
        controls: Dict[str, Any] | None = None,
    ) -> Tuple[np.ndarray, int, Dict[str, Any]]:
        import torch

        self.load()
        inputs = self.processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        ).to(self.device)

        controls = controls or {}
        sample_rate = int(self.model.config.audio_encoder.sampling_rate)
        frame_rate = int(getattr(self.model.config.audio_encoder, "frame_rate", 50))
        max_new_tokens = max(64, int(duration_seconds * frame_rate))

        torch.manual_seed(17000 + int(variation))
        if self.device.startswith("cuda"):
            torch.cuda.manual_seed_all(17000 + int(variation))

        production = controls.get("production") or {}
        syncopation = float(production.get("syncopation", 0.5))
        mix_polish = float(production.get("mix_polish", 0.8))
        guidance_scale = max(1.5, min(5.0, 2.4 + 1.2 * mix_polish))
        temperature = max(0.75, min(1.25, 1.08 - 0.22 * mix_polish + 0.12 * syncopation))

        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                do_sample=True,
                guidance_scale=guidance_scale,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )

        audio = output[0, 0].detach().float().cpu().numpy().astype(np.float32)
        return audio, sample_rate, {
            "backend": "transformers-musicgen",
            "sample_rate": sample_rate,
            "max_new_tokens": max_new_tokens,
            "guidance_scale": round(guidance_scale, 4),
            "temperature": round(temperature, 4),
            "structured_controls_received": bool(controls),
            "control_mode": "text-plus-generation-parameters",
        }

    def write_wav(self, path: Path, audio: np.ndarray, sample_rate: int):
        import soundfile as sf

        peak = float(np.max(np.abs(audio)) or 1.0)
        normalized = np.clip(audio / peak * 0.96, -1.0, 1.0)
        sf.write(str(path), normalized, sample_rate, subtype="PCM_16")
