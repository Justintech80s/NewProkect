from __future__ import annotations

import os
from typing import Any, Dict

import numpy as np


class RustDSP:
    """Optional Rust acceleration layer for CPU-heavy DSP primitives.

    Python/NumPy remains the fallback, so the backend works even when the Rust
    extension has not been compiled on a host.
    """

    def __init__(self):
        self.enabled = os.getenv("JUST_MAKER_RUST_DSP_ENABLED", "1").lower() in {
            "1", "true", "yes", "on"
        }
        self._module = None
        self._load_error = None

        if self.enabled:
            try:
                import just_maker_dsp
                self._module = just_maker_dsp
            except Exception as exc:
                self._load_error = exc.__class__.__name__

    @property
    def available(self) -> bool:
        return self.enabled and self._module is not None

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "available": self.available,
            "engine": "rust-pyo3" if self.available else "numpy-fallback",
            "load_error": self._load_error,
        }

    def remove_dc(self, audio: np.ndarray) -> np.ndarray:
        if not self.available:
            return audio - np.mean(audio, axis=0, keepdims=True)

        channels = audio.shape[1] if audio.ndim == 2 else 1
        flat = np.asarray(audio, dtype=np.float32).reshape(-1)
        result = self._module.remove_dc_interleaved(flat.tolist(), channels)
        return np.asarray(result, dtype=np.float32).reshape(audio.shape)

    def high_pass(self, audio: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
        if not self.available:
            return self._numpy_high_pass(audio, sr, cutoff_hz)

        channels = audio.shape[1] if audio.ndim == 2 else 1
        flat = np.asarray(audio, dtype=np.float32).reshape(-1)
        result = self._module.high_pass_interleaved(
            flat.tolist(),
            channels,
            float(sr),
            float(cutoff_hz),
        )
        return np.asarray(result, dtype=np.float32).reshape(audio.shape)

    def apply_gain_db(self, audio: np.ndarray, gain_db: float) -> np.ndarray:
        if not self.available:
            return audio * (10.0 ** (float(gain_db) / 20.0))

        flat = np.asarray(audio, dtype=np.float32).reshape(-1)
        result = self._module.apply_gain_db_interleaved(flat.tolist(), float(gain_db))
        return np.asarray(result, dtype=np.float32).reshape(audio.shape)

    def soft_clip(self, audio: np.ndarray, drive: float = 1.22) -> np.ndarray:
        if not self.available:
            return np.tanh(audio * drive) / np.tanh(drive)

        flat = np.asarray(audio, dtype=np.float32).reshape(-1)
        result = self._module.soft_clip_interleaved(flat.tolist(), float(drive))
        return np.asarray(result, dtype=np.float32).reshape(audio.shape)

    def normalize_peak(self, audio: np.ndarray, target_peak_db: float) -> np.ndarray:
        if not self.available:
            target = 10.0 ** (float(target_peak_db) / 20.0)
            peak = float(np.max(np.abs(audio)) or 1.0)
            return audio / peak * target

        flat = np.asarray(audio, dtype=np.float32).reshape(-1)
        result = self._module.normalize_peak_interleaved(
            flat.tolist(),
            float(target_peak_db),
        )
        return np.asarray(result, dtype=np.float32).reshape(audio.shape)

    def rms_dbfs(self, audio: np.ndarray) -> float:
        if not self.available:
            rms = float(np.sqrt(np.mean(audio * audio) + 1e-12))
            return float(20.0 * np.log10(rms + 1e-12))

        flat = np.asarray(audio, dtype=np.float32).reshape(-1)
        return float(self._module.rms_dbfs(flat.tolist()))

    def peak_dbfs(self, audio: np.ndarray) -> float:
        if not self.available:
            peak = float(np.max(np.abs(audio)) + 1e-12)
            return float(20.0 * np.log10(peak + 1e-12))

        flat = np.asarray(audio, dtype=np.float32).reshape(-1)
        return float(self._module.peak_dbfs(flat.tolist()))

    def _numpy_high_pass(
        self,
        audio: np.ndarray,
        sr: int,
        cutoff_hz: float,
    ) -> np.ndarray:
        if len(audio) < 2:
            return audio
        rc = 1.0 / (2.0 * np.pi * max(10.0, cutoff_hz))
        dt = 1.0 / sr
        alpha = rc / (rc + dt)
        out = np.empty_like(audio)
        out[0] = audio[0]
        for i in range(1, len(audio)):
            out[i] = alpha * (out[i - 1] + audio[i] - audio[i - 1])
        return out
