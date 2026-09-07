from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import numpy as np


MIN_SAMPLE_RATE = 8_000
MAX_SAMPLE_RATE = 192_000
MAX_AUDIO_SECONDS = 1_800
MAX_CHANNELS = 2


class AudioValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AudioTechnicalMetadata:
    sample_rate: int
    channels: int
    frames: int
    duration_seconds: float
    peak_linear: float
    peak_dbfs: float
    rms_dbfs: float
    finite: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "frames": self.frames,
            "duration_seconds": round(self.duration_seconds, 6),
            "peak_linear": round(self.peak_linear, 8),
            "peak_dbfs": round(self.peak_dbfs, 4),
            "rms_dbfs": round(self.rms_dbfs, 4),
            "finite": self.finite,
        }


def validate_audio_array(
    audio: np.ndarray,
    sample_rate: int,
    *,
    allow_empty: bool = False,
) -> AudioTechnicalMetadata:
    if not isinstance(audio, np.ndarray):
        raise AudioValidationError("audio_must_be_numpy_array")
    if audio.ndim == 1:
        channels = 1
        frames = int(audio.shape[0])
    elif audio.ndim == 2:
        frames = int(audio.shape[0])
        channels = int(audio.shape[1])
    else:
        raise AudioValidationError("unsupported_audio_rank")

    if channels < 1 or channels > MAX_CHANNELS:
        raise AudioValidationError("unsupported_channel_count")
    if sample_rate < MIN_SAMPLE_RATE or sample_rate > MAX_SAMPLE_RATE:
        raise AudioValidationError("unsupported_sample_rate")
    if frames == 0 and not allow_empty:
        raise AudioValidationError("empty_audio")

    duration = (frames / float(sample_rate)) if sample_rate else 0.0
    if duration > MAX_AUDIO_SECONDS:
        raise AudioValidationError("audio_too_long")

    finite = bool(np.isfinite(audio).all())
    if not finite:
        raise AudioValidationError("non_finite_audio")

    if frames:
        peak = float(np.max(np.abs(audio)))
        rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64)) + 1e-12))
    else:
        peak = 0.0
        rms = 0.0

    peak_dbfs = -120.0 if peak <= 1e-12 else float(20.0 * np.log10(peak))
    rms_dbfs = -120.0 if rms <= 1e-12 else float(20.0 * np.log10(rms))

    return AudioTechnicalMetadata(
        sample_rate=int(sample_rate),
        channels=channels,
        frames=frames,
        duration_seconds=duration,
        peak_linear=peak,
        peak_dbfs=peak_dbfs,
        rms_dbfs=rms_dbfs,
        finite=finite,
    )


def ensure_output_safe(audio: np.ndarray, *, limit: float = 1.0) -> np.ndarray:
    if not np.isfinite(audio).all():
        raise AudioValidationError("non_finite_audio")
    if limit <= 0 or limit > 1.0:
        raise AudioValidationError("invalid_output_limit")
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > limit and peak > 0.0:
        audio = audio / peak * limit
    return np.asarray(audio, dtype=np.float32)


def validate_wav_path(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise AudioValidationError("audio_file_not_found")
    if path.suffix.lower() != ".wav":
        raise AudioValidationError("unsupported_audio_container")
