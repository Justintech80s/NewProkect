from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from typing import Dict

import numpy as np


class MasteringEngine:
    """Lightweight production mastering chain with no external DSP dependency."""

    def process(self, audio_path: str, target_peak_db: float = -1.0) -> Dict[str, object]:
        path = Path(audio_path)
        audio, sr = self._read_wav(path)

        if not len(audio):
            return {"audio_path": audio_path, "mastered": False, "reason": "empty_audio"}

        # Remove DC offset.
        audio = audio - float(np.mean(audio))

        # Gentle bus compression using a soft-knee transfer.
        audio = np.tanh(audio * 1.25) / np.tanh(1.25)

        # Peak normalization to approximately -1 dBFS.
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
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)
        return audio, sr

    def _write_wav(self, path: Path, audio: np.ndarray, sr: int):
        pcm = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
