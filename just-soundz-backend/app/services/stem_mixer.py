from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


class StemMixer:
    """Mixes generated mono/stereo PCM WAV stems into a final stereo master bus."""

    def mix(
        self,
        stems: List[Dict[str, Any]],
        stem_arrangement: Dict[str, Any],
    ) -> Dict[str, Any]:
        valid = [s for s in stems if s.get("audio_path")]
        if not valid:
            return {"mixed": False, "reason": "no_generated_stems"}

        loaded = [self._read(Path(s["audio_path"])) for s in valid]
        sample_rates = {sr for _, sr in loaded}
        if len(sample_rates) != 1:
            return {"mixed": False, "reason": "sample_rate_mismatch"}

        sr = sample_rates.pop()
        max_len = max(len(audio) for audio, _ in loaded)
        mix = np.zeros((max_len, 2), dtype=np.float32)
        buses = (stem_arrangement or {}).get("stems") or {}

        for item, (audio, _) in zip(valid, loaded):
            stem = str(item.get("stem") or "unknown")
            bus = buses.get(stem) or {}
            gain_db = float(bus.get("gain_db", -10.0))
            pan = float(bus.get("pan", 0.0))
            gain = 10 ** (gain_db / 20.0)

            stereo = self._to_stereo(audio)
            left_gain = gain * min(1.0, 1.0 - max(0.0, pan))
            right_gain = gain * min(1.0, 1.0 + min(0.0, pan))
            stereo[:, 0] *= left_gain
            stereo[:, 1] *= right_gain

            mix[:len(stereo)] += stereo

        peak = float(np.max(np.abs(mix)) or 1.0)
        if peak > 0.98:
            mix = mix / peak * 0.96

        path = Path(tempfile.gettempdir()) / "just-maker-generated-stems-mix.wav"
        self._write(path, mix, sr)

        return {
            "mixed": True,
            "audio_path": str(path),
            "sample_rate": sr,
            "stem_count": len(valid),
            "stems": [
                {
                    "stem": s.get("stem"),
                    "audio_path": s.get("audio_path"),
                    "provider": s.get("provider"),
                }
                for s in valid
            ],
        }

    def _read(self, path: Path):
        with wave.open(str(path), "rb") as wf:
            sr = wf.getframerate()
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
        if width != 2:
            raise ValueError("StemMixer expects 16-bit PCM WAV")
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        if channels == 2:
            audio = audio.reshape(-1, 2)
        else:
            audio = audio.reshape(-1, 1)
        return audio, sr

    def _to_stereo(self, audio: np.ndarray) -> np.ndarray:
        if audio.ndim == 2 and audio.shape[1] == 2:
            return audio.copy()
        mono = audio[:, 0] if audio.ndim == 2 else audio
        return np.stack([mono, mono], axis=1).astype(np.float32)

    def _write(self, path: Path, audio: np.ndarray, sr: int):
        pcm = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
