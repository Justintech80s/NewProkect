from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from typing import Dict

import numpy as np


class MasteringEngine:
    """Lightweight production mastering chain with no external DSP dependency."""

    def process(
        self,
        audio_path: str,
        target_peak_db: float = -1.0,
        target_rms_db: float = -11.0,
    ) -> Dict[str, object]:
        path = Path(audio_path)
        audio, sr = self._read_wav(path)

        if not len(audio):
            return {"audio_path": audio_path, "mastered": False, "reason": "empty_audio"}

        # Remove DC offset per channel.
        audio = audio - np.mean(audio, axis=0, keepdims=True)

        # Gentle spectral cleanup and bus compression.
        audio = self._high_pass(audio, sr, 25.0)
        pre_rms = float(np.sqrt(np.mean(audio * audio) + 1e-9))
        pre_rms_db = 20.0 * np.log10(pre_rms + 1e-9)
        makeup_db = max(-4.0, min(5.0, target_rms_db - pre_rms_db))
        audio = audio * (10.0 ** (makeup_db / 20.0))
        audio = np.tanh(audio * 1.22) / np.tanh(1.22)

        # Peak normalization.
        target_peak = 10.0 ** (target_peak_db / 20.0)
        peak = float(np.max(np.abs(audio)) or 1.0)
        audio = audio / peak * target_peak

        # Short fade in/out prevents edge clicks.
        fade = min(int(sr * 0.02), len(audio) // 2)
        if fade > 1:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            audio[:fade] *= ramp
            audio[-fade:] *= ramp[::-1]

        out = Path(tempfile.gettempdir()) / f"{path.stem}-mastered.wav"
        self._write_wav(out, audio.astype(np.float32), sr)

        rms = float(np.sqrt(np.mean(audio * audio) + 1e-9))
        crest = float((np.max(np.abs(audio)) + 1e-9) / (rms + 1e-9))

        return {
            "audio_path": str(out),
            "mastered": True,
            "sample_rate": sr,
            "peak_dbfs": round(20.0 * np.log10(float(np.max(np.abs(audio))) + 1e-9), 2),
            "rms_dbfs": round(20.0 * np.log10(rms + 1e-9), 2),
            "crest_factor": round(crest, 3),
            "target_peak_dbfs": target_peak_db,
            "target_rms_dbfs": target_rms_db,
            "makeup_gain_db": round(makeup_db, 2),
            "clipping_detected": bool(np.any(np.abs(audio) >= 0.999)),
        }

    def _read_wav(self, path: Path):
        with wave.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sr = wf.getframerate()
            width = wf.getsampwidth()
            channels = wf.getnchannels()

        if width != 2:
            raise ValueError("Mastering engine currently expects 16-bit PCM WAV.")

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        audio = audio.reshape(-1, channels)
        return audio, sr

    def _write_wav(self, path: Path, audio: np.ndarray, sr: int):
        pcm = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
        channels = audio.shape[1] if audio.ndim == 2 else 1
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())

    def _high_pass(self, audio: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
        if len(audio) < 2:
            return audio
        rc = 1.0 / (2.0 * np.pi * cutoff_hz)
        dt = 1.0 / sr
        alpha = rc / (rc + dt)
        out = np.empty_like(audio)
        out[0] = audio[0]
        for i in range(1, len(audio)):
            out[i] = alpha * (out[i - 1] + audio[i] - audio[i - 1])
        return out
