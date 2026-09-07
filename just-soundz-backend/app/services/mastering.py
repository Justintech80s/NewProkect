from __future__ import annotations

import tempfile
import uuid
import wave
from pathlib import Path
from typing import Dict

import numpy as np

from .audio_safety import (
    AudioValidationError,
    ensure_output_safe,
    validate_audio_array,
    validate_wav_path,
)
from .rust_dsp import RustDSP


class MasteringEngine:
    """Deterministic mastering chain with optional Rust acceleration."""

    OUTPUT_LIMIT = 0.999
    MAX_CORRECTIVE_PASSES = 1

    def __init__(self):
        self.dsp = RustDSP()

    def process(
        self,
        audio_path: str,
        target_peak_db: float = -1.0,
        target_rms_db: float = -11.0,
    ) -> Dict[str, object]:
        path = Path(audio_path)
        validate_wav_path(path)
        audio, sr = self._read_wav(path)
        input_meta = validate_audio_array(audio, sr)

        original_resolved = path.resolve()
        try:
            processed = self._process_array(
                audio,
                sr,
                target_peak_db=target_peak_db,
                target_rms_db=target_rms_db,
            )
            output_meta = validate_audio_array(processed, sr)
            processed = ensure_output_safe(processed, limit=self.OUTPUT_LIMIT)
            output_meta = validate_audio_array(processed, sr)

            out = (
                Path(tempfile.gettempdir())
                / f"{path.stem}-mastered-{uuid.uuid4().hex[:12]}.wav"
            )
            if out.resolve() == original_resolved:
                raise RuntimeError("master_output_must_not_replace_source")
            self._write_wav(out, processed, sr)
            if not out.exists() or out.stat().st_size <= 44:
                raise RuntimeError("master_output_missing")
        except Exception:
            # The source render is never modified or removed by this engine.
            if not path.exists() or path.resolve() != original_resolved:
                raise RuntimeError("source_render_integrity_violation")
            raise

        rms = float(np.sqrt(np.mean(processed * processed) + 1e-12))
        peak = float(np.max(np.abs(processed)) or 0.0)
        crest = float(peak / max(rms, 1e-12))

        return {
            "audio_path": str(out),
            "source_audio_path": str(path),
            "mastered": True,
            "sample_rate": sr,
            "channels": output_meta.channels,
            "duration_seconds": round(output_meta.duration_seconds, 6),
            "peak_dbfs": round(output_meta.peak_dbfs, 2),
            "rms_dbfs": round(output_meta.rms_dbfs, 2),
            "crest_factor": round(crest, 3),
            "target_peak_dbfs": float(target_peak_db),
            "target_rms_dbfs": float(target_rms_db),
            "makeup_gain_db": round(float(self._last_makeup_db), 2),
            "clipping_detected": bool(peak >= self.OUTPUT_LIMIT),
            "input_metadata": input_meta.as_dict(),
            "technical_metadata": output_meta.as_dict(),
            "dsp": self.dsp.status(),
        }

    def _process_array(
        self,
        audio: np.ndarray,
        sr: int,
        *,
        target_peak_db: float,
        target_rms_db: float,
    ) -> np.ndarray:
        validate_audio_array(audio, sr)
        work = np.asarray(audio, dtype=np.float32).copy()

        work = self.dsp.remove_dc(work)
        work = self.dsp.high_pass(work, sr, 25.0)
        validate_audio_array(work, sr)

        pre_rms_db = self.dsp.rms_dbfs(work)
        makeup_db = max(-4.0, min(5.0, float(target_rms_db) - pre_rms_db))
        self._last_makeup_db = makeup_db
        work = self.dsp.apply_gain_db(work, makeup_db)
        work = self.dsp.soft_clip(work, 1.22)
        work = self.dsp.normalize_peak(work, target_peak_db)
        work = ensure_output_safe(work, limit=self.OUTPUT_LIMIT)

        fade = min(int(sr * 0.02), len(work) // 2)
        if fade > 1:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            if work.ndim == 2:
                ramp = ramp[:, None]
            work[:fade] *= ramp
            work[-fade:] *= ramp[::-1]

        return ensure_output_safe(work, limit=self.OUTPUT_LIMIT)

    def _read_wav(self, path: Path):
        try:
            with wave.open(str(path), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                sr = wf.getframerate()
                width = wf.getsampwidth()
                channels = wf.getnchannels()
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

    def _write_wav(self, path: Path, audio: np.ndarray, sr: int):
        validate_audio_array(audio, sr)
        safe = ensure_output_safe(audio, limit=self.OUTPUT_LIMIT)
        pcm = np.clip(safe * 32767.0, -32768, 32767).astype(np.int16)
        channels = safe.shape[1] if safe.ndim == 2 else 1
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
