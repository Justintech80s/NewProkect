from __future__ import annotations

import wave
from pathlib import Path
from typing import Dict, List

import numpy as np


class RepetitionDetector:
    """Detects excessive section similarity in rendered WAV files."""

    def inspect(self, audio_path: str, section_count: int = 8) -> Dict[str, object]:
        path = Path(audio_path)
        if not path.exists():
            return {"score": 0.0, "too_repetitive": False, "reason": "file_missing"}

        audio, _ = self._read_wav(path)
        if len(audio) < section_count * 64:
            return {"score": 0.0, "too_repetitive": False, "reason": "audio_too_short"}

        chunks = [x for x in np.array_split(audio, section_count) if len(x)]
        features = [self._feature(chunk) for chunk in chunks]

        similarities: List[float] = []
        for i in range(len(features) - 1):
            for j in range(i + 1, len(features)):
                similarities.append(self._cosine(features[i], features[j]))

        score = float(np.mean(similarities)) if similarities else 0.0
        return {
            "score": round(score, 4),
            "too_repetitive": score >= 0.92,
            "threshold": 0.92,
            "comparisons": len(similarities),
        }

    def _feature(self, x: np.ndarray) -> np.ndarray:
        x = x.astype(np.float32)
        if not len(x):
            return np.zeros(8, dtype=np.float32)

        frame_count = 8
        pieces = np.array_split(x, frame_count)
        rms = [float(np.sqrt(np.mean(p * p) + 1e-9)) for p in pieces]
        mean_abs = [float(np.mean(np.abs(p))) for p in pieces]
        return np.asarray(rms + mean_abs, dtype=np.float32)

    def _cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom <= 1e-9:
            return 0.0
        return float(np.dot(a, b) / denom)

    def _read_wav(self, path: Path):
        with wave.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sr = wf.getframerate()
            width = wf.getsampwidth()
            channels = wf.getnchannels()

        if width != 2:
            raise ValueError("Repetition detector currently expects 16-bit PCM WAV.")

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)
        return audio, sr
