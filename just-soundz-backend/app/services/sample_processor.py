from __future__ import annotations

import math
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


class SampleProcessor:
    """Processes only rights-cleared local WAV sample assets.

    Supported operations are intentionally dependency-light: slicing, transient-aware
    chopping, reversal accents, simple filtering, and linear-resample time stretching.
    Remote/licensed assets can be handled by a dedicated worker using the same plan.
    """

    def process_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        sample_brain = dict(enriched.get("sample_brain") or {})
        selected = list(sample_brain.get("selected") or [])
        processed: List[Dict[str, Any]] = []

        for index, sample in enumerate(selected):
            if not sample.get("sampling_allowed"):
                continue

            path = self._resolve_local_path(sample)
            if not path:
                processed.append({
                    "id": sample.get("id"),
                    "status": "remote_or_unavailable",
                    "source_uri": sample.get("source_uri"),
                    "storage_uri": sample.get("storage_uri"),
                    "transform": sample.get("transform") or {},
                    "provenance": self._provenance(sample),
                })
                continue

            try:
                result = self.process_file(
                    path,
                    transform=sample.get("transform") or {},
                    variation=index,
                )
                result.update({
                    "id": sample.get("id"),
                    "status": "processed",
                    "provenance": self._provenance(sample),
                })
                processed.append(result)
            except Exception as exc:
                processed.append({
                    "id": sample.get("id"),
                    "status": "failed",
                    "error": exc.__class__.__name__,
                    "provenance": self._provenance(sample),
                })

        sample_brain["processed_samples"] = processed
        enriched["sample_brain"] = sample_brain
        return enriched

    def process_file(
        self,
        audio_path: str,
        transform: Dict[str, Any],
        variation: int = 0,
    ) -> Dict[str, Any]:
        source = Path(audio_path)
        audio, sr = self._read_wav(source)

        ratio = transform.get("time_stretch_ratio")
        if ratio and float(ratio) > 0:
            audio = self._time_stretch(audio, float(ratio))

        chunks = self._chop(audio, pieces=8)
        if variation % 2:
            chunks = list(reversed(chunks))
        if chunks and variation % 3 == 2:
            chunks[min(1, len(chunks) - 1)] = chunks[min(1, len(chunks) - 1)][::-1]

        audio = np.concatenate(chunks) if chunks else audio
        audio = self._lowpass(audio, strength=0.18 + 0.04 * (variation % 3))

        peak = float(np.max(np.abs(audio)) or 1.0)
        audio = (audio / peak * 0.88).astype(np.float32)

        out = Path(tempfile.gettempdir()) / f"just-maker-sample-{source.stem}-{variation}.wav"
        self._write_wav(out, audio, sr)

        return {
            "audio_path": str(out),
            "sample_rate": sr,
            "duration_seconds": round(len(audio) / sr, 4),
            "transform": transform,
        }

    def _resolve_local_path(self, sample: Dict[str, Any]) -> str | None:
        for key in ("audio_path", "storage_uri", "source_uri"):
            value = sample.get(key)
            if not value:
                continue
            value = str(value)
            if value.startswith("file://"):
                value = value[7:]
            path = Path(value)
            if path.exists() and path.is_file():
                return str(path)
        return None

    def _provenance(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source_uri": sample.get("source_uri"),
            "storage_uri": sample.get("storage_uri"),
            "rights_status": sample.get("rights_status"),
            "sampling_allowed": bool(sample.get("sampling_allowed", False)),
            "commercial_use": bool(sample.get("commercial_use", False)),
        }

    def _read_wav(self, path: Path):
        with wave.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sr = wf.getframerate()
            width = wf.getsampwidth()
            channels = wf.getnchannels()

        if width != 2:
            raise ValueError("SampleProcessor expects 16-bit PCM WAV")

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

    def _time_stretch(self, audio: np.ndarray, ratio: float) -> np.ndarray:
        target_len = max(1, int(round(len(audio) / ratio)))
        old_x = np.linspace(0.0, 1.0, len(audio), endpoint=False)
        new_x = np.linspace(0.0, 1.0, target_len, endpoint=False)
        return np.interp(new_x, old_x, audio).astype(np.float32)

    def _chop(self, audio: np.ndarray, pieces: int = 8) -> List[np.ndarray]:
        if len(audio) < pieces:
            return [audio]
        chunks = [chunk.copy() for chunk in np.array_split(audio, pieces) if len(chunk)]
        if len(chunks) >= 4:
            order = list(range(len(chunks)))
            for i in range(1, len(order), 4):
                j = min(i + 1, len(order) - 1)
                order[i], order[j] = order[j], order[i]
            chunks = [chunks[i] for i in order]
        return chunks

    def _lowpass(self, audio: np.ndarray, strength: float = 0.2) -> np.ndarray:
        if len(audio) < 2:
            return audio
        strength = max(0.01, min(0.99, float(strength)))
        out = np.empty_like(audio)
        out[0] = audio[0]
        for i in range(1, len(audio)):
            out[i] = strength * audio[i] + (1.0 - strength) * out[i - 1]
        return out
