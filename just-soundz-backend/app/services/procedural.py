from __future__ import annotations

import math
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict

import numpy as np


NOTE_FREQ = {
    "C": 261.63, "C#": 277.18, "DB": 277.18, "D": 293.66, "D#": 311.13,
    "EB": 311.13, "E": 329.63, "F": 349.23, "F#": 369.99, "GB": 369.99,
    "G": 392.00, "G#": 415.30, "AB": 415.30, "A": 440.00, "A#": 466.16,
    "BB": 466.16, "B": 493.88,
}

SEMITONES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class ProceduralMusicProvider:
    """Immediate no-key fallback that renders a real WAV instrumental.

    This is intentionally lightweight. It uses the AI producer plan to drive
    tempo, key, harmony, bass and drum density so Just Soundz can generate audio
    before an external GPU music model is connected.
    """

    name = "built-in-procedural"

    def generate(self, plan: Dict[str, Any], variation: int = 0) -> Dict[str, Any]:
        sample_rate = 22050
        bpm = int(plan.get("bpm") or 100)
        duration = min(int(plan.get("duration_seconds") or 30), 180)
        key = str(plan.get("key") or "C minor")

        rng = np.random.default_rng(1000 + variation)
        t = np.arange(duration * sample_rate, dtype=np.float32) / sample_rate
        audio = np.zeros_like(t)

        beat = 60.0 / bpm
        bar = beat * 4.0

        root_name = key.split()[0].upper().replace("♭", "B").replace("♯", "#")
        scale_minor = "minor" in key.lower()
        root = NOTE_FREQ.get(root_name, NOTE_FREQ["C"])

        # Chord progression: i - VI - III - VII for minor, I - V - vi - IV for major.
        intervals = [0, 8, 3, 10] if scale_minor else [0, 7, 9, 5]
        triad = [0, 3, 7] if scale_minor else [0, 4, 7]

        def semitone(freq: float, n: int) -> float:
            return freq * (2.0 ** (n / 12.0))

        # Harmony pad.
        for bar_idx in range(max(1, math.ceil(duration / bar))):
            start_s = bar_idx * bar
            end_s = min(duration, start_s + bar)
            if start_s >= duration:
                break
            chord_root = semitone(root / 2.0, intervals[bar_idx % len(intervals)])
            mask = (t >= start_s) & (t < end_s)
            local = t[mask] - start_s
            env = np.minimum(local / 0.08, 1.0) * np.minimum((end_s - start_s - local) / 0.15, 1.0)
            env = np.clip(env, 0.0, 1.0)
            chord = np.zeros_like(local)
            for n in triad:
                f = semitone(chord_root, n)
                chord += np.sin(2 * np.pi * f * local)
                chord += 0.25 * np.sin(2 * np.pi * f * 2 * local)
            audio[mask] += 0.07 * chord * env

        # Bass on beats 1 and 3.
        for i in range(int(duration / beat) + 1):
            start_s = i * beat
            if i % 2 != 0 or start_s >= duration:
                continue
            chord_idx = int(start_s / bar) % len(intervals)
            f = semitone(root / 4.0, intervals[chord_idx])
            length = min(beat * 0.8, duration - start_s)
            n = int(length * sample_rate)
            if n <= 0:
                continue
            local = np.arange(n, dtype=np.float32) / sample_rate
            env = np.exp(-4.5 * local / max(length, 1e-3))
            tone = np.sin(2 * np.pi * f * local) + 0.25 * np.sin(2 * np.pi * f * 2 * local)
            idx = int(start_s * sample_rate)
            audio[idx:idx+n] += 0.16 * tone * env

        # Kick, snare, hats.
        step = beat / 2.0
        total_steps = int(duration / step) + 1
        sparse = plan.get("drums", {}).get("density") == "sparse"
        for i in range(total_steps):
            start_s = i * step
            if start_s >= duration:
                break
            beat_pos = i % 8

            if beat_pos in (0, 4) or (not sparse and beat_pos == 6 and rng.random() > 0.65):
                self._add_kick(audio, sample_rate, start_s)

            if beat_pos in (2, 6):
                self._add_snare(audio, sample_rate, start_s, rng)

            if not sparse or beat_pos % 2 == 0:
                self._add_hat(audio, sample_rate, start_s, rng)

        # Gentle saturation and normalization.
        audio = np.tanh(audio * 1.35)
        peak = float(np.max(np.abs(audio)) or 1.0)
        audio = (audio / peak * 0.92).astype(np.float32)

        path = Path(tempfile.gettempdir()) / f"just-soundz-{variation}.wav"
        self._write_wav(path, audio, sample_rate)

        return {
            "provider": self.name,
            "audio_path": str(path),
            "metadata": {
                "sample_rate": sample_rate,
                "bpm": bpm,
                "key": key,
                "duration_seconds": duration,
                "variation": variation,
            },
        }

    def _add_kick(self, audio, sr, start_s):
        length = 0.22
        n = min(int(length * sr), len(audio) - int(start_s * sr))
        if n <= 0:
            return
        tt = np.arange(n, dtype=np.float32) / sr
        freq = 120 * np.exp(-18 * tt) + 42
        phase = 2 * np.pi * np.cumsum(freq) / sr
        env = np.exp(-14 * tt)
        x = np.sin(phase) * env
        idx = int(start_s * sr)
        audio[idx:idx+n] += 0.5 * x

    def _add_snare(self, audio, sr, start_s, rng):
        length = 0.16
        n = min(int(length * sr), len(audio) - int(start_s * sr))
        if n <= 0:
            return
        tt = np.arange(n, dtype=np.float32) / sr
        noise = rng.normal(0, 1, n).astype(np.float32)
        body = np.sin(2 * np.pi * 180 * tt)
        env = np.exp(-18 * tt)
        x = (0.75 * noise + 0.25 * body) * env
        idx = int(start_s * sr)
        audio[idx:idx+n] += 0.20 * x

    def _add_hat(self, audio, sr, start_s, rng):
        length = 0.045
        n = min(int(length * sr), len(audio) - int(start_s * sr))
        if n <= 0:
            return
        tt = np.arange(n, dtype=np.float32) / sr
        noise = rng.normal(0, 1, n).astype(np.float32)
        env = np.exp(-70 * tt)
        x = noise * env
        idx = int(start_s * sr)
        audio[idx:idx+n] += 0.055 * x

    def _write_wav(self, path: Path, audio: np.ndarray, sr: int):
        pcm = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
