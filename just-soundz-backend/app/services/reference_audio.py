from __future__ import annotations

import wave
from pathlib import Path
from typing import Any, Dict

import numpy as np


class ReferenceAudioAnalyzer:
    """Extracts broad production traits from a cleared/user-owned WAV reference.

    It intentionally avoids storing or reproducing melodic note sequences.
    """

    def analyze(self, audio_path: str) -> Dict[str, Any]:
        path = Path(audio_path)
        audio, sr = self._read_wav(path)
        if len(audio) < 64:
            raise ValueError("Reference audio is too short")

        mono = audio.mean(axis=1) if audio.ndim == 2 else audio
        peak = float(np.max(np.abs(mono)) + 1e-12)
        rms = float(np.sqrt(np.mean(mono * mono) + 1e-12))
        crest = float(peak / max(rms, 1e-12))

        centroid = self._spectral_centroid(mono, sr)
        low_ratio, mid_ratio, high_ratio = self._band_energy(mono, sr)
        onset_density = self._onset_density(mono, sr)
        transient_strength = self._transient_strength(mono)
        dynamic_range = max(0.0, min(1.0, (crest - 1.0) / 5.0))

        brightness = max(0.0, min(1.0, centroid / 7000.0))
        low_end_weight = max(0.0, min(1.0, low_ratio * 1.6))
        density = max(0.0, min(1.0, onset_density / 8.0))
        punch = max(0.0, min(1.0, transient_strength * 5.0))

        return {
            "source": str(path),
            "sample_rate": sr,
            "duration_seconds": round(len(mono) / sr, 4),
            "rms_dbfs": round(20.0 * np.log10(rms + 1e-12), 2),
            "peak_dbfs": round(20.0 * np.log10(peak + 1e-12), 2),
            "crest_factor": round(crest, 4),
            "spectral_centroid_hz": round(centroid, 2),
            "band_energy": {
                "low": round(low_ratio, 4),
                "mid": round(mid_ratio, 4),
                "high": round(high_ratio, 4),
            },
            "production_traits": {
                "brightness": round(brightness, 4),
                "low_end_weight": round(low_end_weight, 4),
                "rhythmic_density": round(density, 4),
                "transient_punch": round(punch, 4),
                "dynamic_range": round(dynamic_range, 4),
                "mix_polish_hint": round(
                    max(0.0, min(1.0, 0.55 + 0.25 * dynamic_range - 0.15 * high_ratio)),
                    4,
                ),
            },
            "policy": {
                "melody_extracted": False,
                "note_sequence_stored": False,
                "production_traits_only": True,
            },
        }

    def _read_wav(self, path: Path):
        with wave.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sr = wf.getframerate()
            channels = wf.getnchannels()
            width = wf.getsampwidth()

        if width != 2:
            raise ValueError("ReferenceAudioAnalyzer expects 16-bit PCM WAV")

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        audio = audio.reshape(-1, channels)
        return audio, sr

    def _spectral_centroid(self, mono: np.ndarray, sr: int) -> float:
        segment = mono[: min(len(mono), sr * 20)]
        spectrum = np.abs(np.fft.rfft(segment))
        freqs = np.fft.rfftfreq(len(segment), 1.0 / sr)
        return float(np.sum(freqs * spectrum) / (np.sum(spectrum) + 1e-12))

    def _band_energy(self, mono: np.ndarray, sr: int):
        segment = mono[: min(len(mono), sr * 20)]
        spectrum = np.abs(np.fft.rfft(segment)) ** 2
        freqs = np.fft.rfftfreq(len(segment), 1.0 / sr)
        total = float(np.sum(spectrum) + 1e-12)

        low = float(np.sum(spectrum[(freqs >= 20) & (freqs < 250)]) / total)
        mid = float(np.sum(spectrum[(freqs >= 250) & (freqs < 2500)]) / total)
        high = float(np.sum(spectrum[(freqs >= 2500)]) / total)
        return low, mid, high

    def _onset_density(self, mono: np.ndarray, sr: int) -> float:
        hop = max(64, int(sr * 0.01))
        frame = max(hop * 2, int(sr * 0.02))
        if len(mono) < frame:
            return 0.0

        energies = []
        for i in range(0, len(mono) - frame, hop):
            chunk = mono[i:i + frame]
            energies.append(float(np.mean(chunk * chunk)))
        if len(energies) < 3:
            return 0.0

        diff = np.maximum(0.0, np.diff(np.asarray(energies)))
        threshold = float(np.mean(diff) + 1.5 * np.std(diff))
        onsets = int(np.sum(diff > threshold))
        seconds = len(mono) / sr
        return onsets / max(seconds, 1e-6)

    def _transient_strength(self, mono: np.ndarray) -> float:
        if len(mono) < 2:
            return 0.0
        diff = np.abs(np.diff(mono))
        return float(np.percentile(diff, 95))
