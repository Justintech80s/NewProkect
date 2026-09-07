from __future__ import annotations

import tempfile
import uuid
import wave
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from .audio_safety import (
    AudioValidationError,
    ensure_output_safe,
    validate_audio_array,
    validate_wav_path,
)
from .rust_dsp import RustDSP


class StemMixer:
    """Validates, gain-stages, and mixes generated stems safely."""

    PREMIX_PEAK_LIMIT = 0.85
    OUTPUT_PEAK_LIMIT = 0.96

    def __init__(self):
        self.dsp = RustDSP()

    def mix(
        self,
        stems: List[Dict[str, Any]],
        stem_arrangement: Dict[str, Any],
    ) -> Dict[str, Any]:
        buses = (stem_arrangement or {}).get("stems") or {}
        requested = [str(name) for name in buses.keys()]
        supplied_names = [str(s.get("stem") or "unknown") for s in stems]
        missing_stems = [name for name in requested if name not in supplied_names]

        invalid_stems: List[Dict[str, str]] = []
        valid: List[Dict[str, Any]] = []
        loaded: List[tuple[np.ndarray, int]] = []

        for item in stems:
            stem_name = str(item.get("stem") or "unknown")
            audio_path = item.get("audio_path")
            if not audio_path:
                invalid_stems.append({"stem": stem_name, "reason": "missing_audio_path"})
                continue
            try:
                audio, sr = self._read(Path(str(audio_path)))
            except (AudioValidationError, OSError, wave.Error) as exc:
                invalid_stems.append({"stem": stem_name, "reason": str(exc)})
                continue
            valid.append(item)
            loaded.append((audio, sr))

        if not valid:
            return {
                "mixed": False,
                "reason": "no_valid_stems",
                "partial": bool(missing_stems or invalid_stems),
                "missing_stems": missing_stems,
                "invalid_stems": invalid_stems,
            }

        sample_rates = {sr for _, sr in loaded}
        if len(sample_rates) != 1:
            return {
                "mixed": False,
                "reason": "sample_rate_mismatch",
                "partial": True,
                "missing_stems": missing_stems,
                "invalid_stems": invalid_stems,
            }

        sr = sample_rates.pop()
        max_len = max(len(audio) for audio, _ in loaded)
        mix = np.zeros((max_len, 2), dtype=np.float32)
        per_stem_meta: List[Dict[str, Any]] = []

        for item, (audio, _) in zip(valid, loaded):
            stem = str(item.get("stem") or "unknown")
            bus = buses.get(stem) or {}
            gain_db = float(bus.get("gain_db", -10.0))
            pan = max(-1.0, min(1.0, float(bus.get("pan", 0.0))))
            gain = 10 ** (gain_db / 20.0)

            stereo = self._to_stereo(audio)
            eq = bus.get("eq") or {}
            high_pass_hz = float(eq.get("high_pass_hz", 0.0))
            if high_pass_hz > 0:
                stereo = self.dsp.high_pass(stereo, sr, high_pass_hz)

            if float(eq.get("mud_cut_db", 0.0)) < 0:
                stereo = self._tilt_reduce_low_mids(stereo, amount=0.08)
            if float(eq.get("harshness_cut_db", 0.0)) < 0:
                stereo = self._smooth_highs(stereo, amount=0.12)

            left_gain = gain * min(1.0, 1.0 - max(0.0, pan))
            right_gain = gain * min(1.0, 1.0 + min(0.0, pan))
            stereo[:, 0] *= left_gain
            stereo[:, 1] *= right_gain

            if (bus.get("limiter") or {}).get("enabled"):
                stereo = self.dsp.soft_clip(stereo, 1.15)

            stereo = self._premix_bound(stereo)
            meta = validate_audio_array(stereo, sr).as_dict()
            per_stem_meta.append({
                "stem": stem,
                "provider": item.get("provider"),
                "technical_metadata": meta,
            })
            mix[: len(stereo)] += stereo

        mix = self._premix_bound(mix)
        mix = ensure_output_safe(mix, limit=self.OUTPUT_PEAK_LIMIT)
        output_meta = validate_audio_array(mix, sr)

        path = (
            Path(tempfile.gettempdir())
            / f"just-maker-generated-stems-mix-{uuid.uuid4().hex[:12]}.wav"
        )
        self._write(path, mix, sr)
        if not path.exists() or path.stat().st_size <= 44:
            raise RuntimeError("stem_mix_output_missing")

        return {
            "mixed": True,
            "audio_path": str(path),
            "sample_rate": sr,
            "stem_count": len(valid),
            "requested_stem_count": len(requested),
            "partial": bool(missing_stems or invalid_stems),
            "missing_stems": missing_stems,
            "invalid_stems": invalid_stems,
            "technical_metadata": output_meta.as_dict(),
            "dsp": self.dsp.status(),
            "stems": per_stem_meta,
        }

    def _premix_bound(self, audio: np.ndarray) -> np.ndarray:
        if not np.isfinite(audio).all():
            raise AudioValidationError("non_finite_audio")
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak > self.PREMIX_PEAK_LIMIT and peak > 0.0:
            audio = audio / peak * self.PREMIX_PEAK_LIMIT
        return np.asarray(audio, dtype=np.float32)

    def _read(self, path: Path):
        validate_wav_path(path)
        try:
            with wave.open(str(path), "rb") as wf:
                sr = wf.getframerate()
                channels = wf.getnchannels()
                width = wf.getsampwidth()
                frames = wf.readframes(wf.getnframes())
        except (wave.Error, EOFError) as exc:
            raise AudioValidationError("malformed_wav") from exc

        if width != 2:
            raise AudioValidationError("unsupported_sample_width")
        if channels not in {1, 2}:
            raise AudioValidationError("unsupported_channel_count")

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        audio = audio.reshape(-1, channels)
        validate_audio_array(audio, sr)
        return audio, sr

    def _to_stereo(self, audio: np.ndarray) -> np.ndarray:
        if audio.ndim == 2 and audio.shape[1] == 2:
            return audio.copy()
        mono = audio[:, 0] if audio.ndim == 2 else audio
        return np.stack([mono, mono], axis=1).astype(np.float32)

    def _tilt_reduce_low_mids(self, audio: np.ndarray, amount: float) -> np.ndarray:
        delayed = np.vstack([audio[:1], audio[:-1]])
        low = 0.5 * audio + 0.5 * delayed
        return audio - low * float(amount)

    def _smooth_highs(self, audio: np.ndarray, amount: float) -> np.ndarray:
        if len(audio) < 2:
            return audio
        smooth = audio.copy()
        smooth[1:] = 0.5 * audio[1:] + 0.5 * audio[:-1]
        return audio * (1.0 - amount) + smooth * amount

    def _write(self, path: Path, audio: np.ndarray, sr: int):
        validate_audio_array(audio, sr)
        safe = ensure_output_safe(audio, limit=self.OUTPUT_PEAK_LIMIT)
        pcm = np.clip(safe * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
