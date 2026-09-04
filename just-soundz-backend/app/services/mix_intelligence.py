from __future__ import annotations

import wave
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


class MixIntelligence:
    """Analyzes generated stems and recommends corrective mix moves."""

    TARGET_RMS = {
        "drums": -15.0,
        "bass": -18.0,
        "harmony": -22.0,
        "lead": -21.0,
        "texture": -27.0,
        "fx": -30.0,
    }

    def analyze_stems(self, stems: List[Dict[str, Any]]) -> Dict[str, Any]:
        reports = []
        for stem in stems:
            path = stem.get("audio_path")
            if not path:
                continue
            try:
                audio, sr = self._read(Path(path))
                mono = audio.mean(axis=1) if audio.ndim == 2 else audio
                rms = float(np.sqrt(np.mean(mono * mono) + 1e-12))
                peak = float(np.max(np.abs(mono)) + 1e-12)
                rms_db = 20.0 * np.log10(rms + 1e-12)
                peak_db = 20.0 * np.log10(peak + 1e-12)
                centroid = self._spectral_centroid(mono, sr)

                name = str(stem.get("stem") or "unknown")
                target = self.TARGET_RMS.get(name, -22.0)
                gain_adjust = max(-6.0, min(6.0, target - rms_db))

                reports.append({
                    "stem": name,
                    "rms_dbfs": round(rms_db, 2),
                    "peak_dbfs": round(peak_db, 2),
                    "spectral_centroid_hz": round(centroid, 1),
                    "recommended_gain_db": round(gain_adjust, 2),
                    "clipping_risk": peak_db > -0.3,
                    "mud_risk": centroid < 900 and name not in {"bass"},
                    "harshness_risk": centroid > 5200 and name not in {"fx", "texture"},
                })
            except Exception as exc:
                reports.append({
                    "stem": stem.get("stem"),
                    "error": exc.__class__.__name__,
                })

        return {
            "stems": reports,
            "issues": self._issues(reports),
        }

    def apply_bus_corrections(
        self,
        stem_arrangement: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        adjusted = {
            **(stem_arrangement or {}),
            "stems": {
                k: dict(v)
                for k, v in ((stem_arrangement or {}).get("stems") or {}).items()
            },
        }

        for report in analysis.get("stems") or []:
            stem = report.get("stem")
            if not stem or stem not in adjusted["stems"] or report.get("error"):
                continue
            bus = adjusted["stems"][stem]
            bus["gain_db"] = round(
                float(bus.get("gain_db", -10.0))
                + float(report.get("recommended_gain_db", 0.0)),
                2,
            )
            bus["eq"] = {
                "high_pass_hz": 35 if stem == "bass" else 70 if stem == "drums" else 110,
                "mud_cut_db": -1.8 if report.get("mud_risk") else 0.0,
                "harshness_cut_db": -1.5 if report.get("harshness_risk") else 0.0,
            }
            bus["limiter"] = {
                "enabled": bool(report.get("clipping_risk")),
                "ceiling_dbfs": -1.0,
            }

        adjusted["mix_analysis"] = analysis
        return adjusted

    def _issues(self, reports: List[Dict[str, Any]]) -> List[str]:
        issues = []
        if any(r.get("clipping_risk") for r in reports):
            issues.append("stem_clipping_risk")
        if any(r.get("mud_risk") for r in reports):
            issues.append("low_mid_mud")
        if any(r.get("harshness_risk") for r in reports):
            issues.append("high_frequency_harshness")
        return issues

    def _read(self, path: Path):
        with wave.open(str(path), "rb") as wf:
            sr = wf.getframerate()
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
        if width != 2:
            raise ValueError("MixIntelligence expects 16-bit PCM WAV")
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        audio = audio.reshape(-1, channels)
        return audio, sr

    def _spectral_centroid(self, mono: np.ndarray, sr: int) -> float:
        if len(mono) < 64:
            return 0.0
        segment = mono[: min(len(mono), sr * 20)]
        spectrum = np.abs(np.fft.rfft(segment))
        freqs = np.fft.rfftfreq(len(segment), 1.0 / sr)
        denom = float(np.sum(spectrum) + 1e-12)
        return float(np.sum(freqs * spectrum) / denom)
