from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np
import pytest

from app.services.audio_safety import AudioValidationError, validate_audio_array
from app.services.mastering import MasteringEngine
from app.services.mastering_critic import MasteringCritic
from app.services.rust_dsp import RustDSP
from app.services.stem_mixer import StemMixer


def write_wav(
    path: Path,
    audio: np.ndarray,
    *,
    sample_rate: int = 44_100,
    channels: int = 1,
) -> Path:
    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 1:
        if channels == 2:
            arr = np.stack([arr, arr], axis=1)
        else:
            arr = arr[:, None]
    pcm = np.clip(arr * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return path


def sine(seconds=0.25, sr=44_100, amplitude=0.5, dc=0.0):
    t = np.arange(int(seconds * sr), dtype=np.float32) / sr
    return (amplitude * np.sin(2.0 * np.pi * 220.0 * t) + dc).astype(np.float32)


def test_mastering_silence_is_finite_and_preserves_source(tmp_path):
    source = write_wav(tmp_path / "silence.wav", np.zeros(4_410, dtype=np.float32))
    original = source.read_bytes()
    result = MasteringEngine().process(str(source))
    assert result["mastered"] is True
    assert result["technical_metadata"]["finite"] is True
    assert Path(result["audio_path"]).exists()
    assert Path(result["audio_path"]).resolve() != source.resolve()
    assert source.read_bytes() == original


def test_mastering_clipped_input_produces_bounded_output(tmp_path):
    source = write_wav(tmp_path / "clipped.wav", np.ones(8_820, dtype=np.float32))
    result = MasteringEngine().process(str(source))
    assert result["technical_metadata"]["peak_linear"] <= 0.999001
    assert result["peak_dbfs"] <= -0.3


def test_mastering_removes_dc_offset(tmp_path):
    source = write_wav(tmp_path / "dc.wav", sine(dc=0.35, amplitude=0.1))
    engine = MasteringEngine()
    mastered = engine.process(str(source))
    output, sr = engine._read_wav(Path(mastered["audio_path"]))
    validate_audio_array(output, sr)
    assert abs(float(np.mean(output))) < 0.02


def test_mastering_accepts_short_but_valid_audio(tmp_path):
    source = write_wav(tmp_path / "short.wav", sine(seconds=0.03))
    result = MasteringEngine().process(str(source))
    assert result["mastered"] is True
    assert result["duration_seconds"] > 0.0


def test_mastering_rejects_malformed_wav(tmp_path):
    path = tmp_path / "broken.wav"
    path.write_bytes(b"not a wav file")
    with pytest.raises(AudioValidationError):
        MasteringEngine().process(str(path))


def test_mastering_rejects_empty_wav(tmp_path):
    path = write_wav(tmp_path / "empty.wav", np.zeros(0, dtype=np.float32))
    with pytest.raises(AudioValidationError):
        MasteringEngine().process(str(path))


def test_dsp_failure_never_overwrites_original(tmp_path, monkeypatch):
    source = write_wav(tmp_path / "original.wav", sine())
    before = source.read_bytes()
    engine = MasteringEngine()

    def explode(_audio):
        raise RuntimeError("synthetic_dsp_failure")

    monkeypatch.setattr(engine.dsp, "remove_dc", explode)
    with pytest.raises(RuntimeError, match="synthetic_dsp_failure"):
        engine.process(str(source))
    assert source.exists()
    assert source.read_bytes() == before


def test_non_finite_audio_is_rejected():
    with pytest.raises(AudioValidationError, match="non_finite_audio"):
        validate_audio_array(np.array([[0.0], [np.nan]], dtype=np.float32), 44_100)


def test_stem_mixer_reports_missing_stems(tmp_path):
    drums = write_wav(tmp_path / "drums.wav", sine(amplitude=0.3))
    result = StemMixer().mix(
        [{"stem": "drums", "audio_path": str(drums), "provider": "fixture"}],
        {
            "stems": {
                "drums": {"gain_db": -6.0},
                "bass": {"gain_db": -8.0},
            }
        },
    )
    assert result["mixed"] is True
    assert result["partial"] is True
    assert result["missing_stems"] == ["bass"]


def test_stem_mixer_reports_invalid_stem_file(tmp_path):
    broken = tmp_path / "broken.wav"
    broken.write_bytes(b"bad")
    result = StemMixer().mix(
        [{"stem": "drums", "audio_path": str(broken)}],
        {"stems": {"drums": {}}},
    )
    assert result["mixed"] is False
    assert result["invalid_stems"][0]["stem"] == "drums"


def test_multi_stem_mix_is_finite_stereo_and_bounded(tmp_path):
    drums = write_wav(tmp_path / "drums.wav", sine(amplitude=0.95))
    bass = write_wav(
        tmp_path / "bass.wav",
        sine(amplitude=0.95) * 0.9,
        channels=2,
    )
    result = StemMixer().mix(
        [
            {"stem": "drums", "audio_path": str(drums), "provider": "fixture"},
            {"stem": "bass", "audio_path": str(bass), "provider": "fixture"},
        ],
        {
            "stems": {
                "drums": {"gain_db": 0.0, "pan": -0.2},
                "bass": {"gain_db": 0.0, "pan": 0.2},
            }
        },
    )
    assert result["mixed"] is True
    assert result["partial"] is False
    assert result["technical_metadata"]["channels"] == 2
    assert result["technical_metadata"]["finite"] is True
    assert result["technical_metadata"]["peak_linear"] <= 0.960001


def test_stem_mixer_rejects_sample_rate_mismatch(tmp_path):
    one = write_wav(tmp_path / "one.wav", sine(sr=44_100), sample_rate=44_100)
    two = write_wav(
        tmp_path / "two.wav",
        sine(sr=48_000),
        sample_rate=48_000,
    )
    result = StemMixer().mix(
        [
            {"stem": "drums", "audio_path": str(one)},
            {"stem": "bass", "audio_path": str(two)},
        ],
        {"stems": {"drums": {}, "bass": {}}},
    )
    assert result["mixed"] is False
    assert result["reason"] == "sample_rate_mismatch"


def test_mastering_critic_correction_cap_is_deterministic():
    critic = MasteringCritic()
    review = critic.evaluate(
        {
            "mastered": True,
            "peak_dbfs": -0.1,
            "rms_dbfs": -10.0,
            "crest_factor": 2.0,
        }
    )
    assert critic.should_correct(review, 0) is True
    assert critic.should_correct(review, 1) is False
    assert critic.MAX_CORRECTIVE_PASSES == 1


class FakeRustModule:
    @staticmethod
    def remove_dc_interleaved(samples, channels):
        arr = np.asarray(samples, dtype=np.float32).reshape(-1, channels)
        return (arr - np.mean(arr, axis=0, keepdims=True)).reshape(-1).tolist()

    @staticmethod
    def high_pass_interleaved(samples, channels, sample_rate, cutoff_hz):
        arr = np.asarray(samples, dtype=np.float32).reshape(-1, channels)
        if len(arr) < 2:
            return arr.reshape(-1).tolist()
        rc = 1.0 / (2.0 * np.pi * max(10.0, cutoff_hz))
        dt = 1.0 / sample_rate
        alpha = rc / (rc + dt)
        out = np.empty_like(arr)
        out[0] = arr[0]
        for i in range(1, len(arr)):
            out[i] = alpha * (out[i - 1] + arr[i] - arr[i - 1])
        return out.reshape(-1).tolist()

    @staticmethod
    def apply_gain_db_interleaved(samples, gain_db):
        gain = 10.0 ** (gain_db / 20.0)
        return (np.asarray(samples, dtype=np.float32) * gain).tolist()

    @staticmethod
    def soft_clip_interleaved(samples, drive):
        arr = np.asarray(samples, dtype=np.float32)
        result = np.tanh(arr * drive) / np.tanh(drive)
        return np.clip(result, -1.0, 1.0).tolist()

    @staticmethod
    def normalize_peak_interleaved(samples, target_peak_db):
        arr = np.asarray(samples, dtype=np.float32)
        if arr.size == 0:
            return arr.tolist()
        peak = max(float(np.max(np.abs(arr))), 1e-12)
        target = 10.0 ** (target_peak_db / 20.0)
        return (arr / peak * target).tolist()

    @staticmethod
    def rms_dbfs(samples):
        arr = np.asarray(samples, dtype=np.float32)
        if arr.size == 0:
            return -120.0
        rms = math.sqrt(float(np.mean(arr * arr)) + 1e-12)
        return 20.0 * math.log10(rms + 1e-12)

    @staticmethod
    def peak_dbfs(samples):
        arr = np.asarray(samples, dtype=np.float32)
        if arr.size == 0:
            return -120.0
        return 20.0 * math.log10(float(np.max(np.abs(arr))) + 1e-12)


def test_rust_and_numpy_dsp_paths_are_compatible():
    audio = np.stack([sine(seconds=0.05), sine(seconds=0.05) * 0.7], axis=1)

    numpy_dsp = RustDSP()
    numpy_dsp.enabled = False
    numpy_dsp._module = None

    rust_dsp = RustDSP()
    rust_dsp.enabled = True
    rust_dsp._module = FakeRustModule()

    numpy_result = numpy_dsp.normalize_peak(
        numpy_dsp.soft_clip(
            numpy_dsp.high_pass(numpy_dsp.remove_dc(audio), 44_100, 25.0),
            1.22,
        ),
        -1.0,
    )
    rust_result = rust_dsp.normalize_peak(
        rust_dsp.soft_clip(
            rust_dsp.high_pass(rust_dsp.remove_dc(audio), 44_100, 25.0),
            1.22,
        ),
        -1.0,
    )

    assert np.isfinite(numpy_result).all()
    assert np.isfinite(rust_result).all()
    assert float(np.max(np.abs(numpy_result))) <= 1.0
    assert float(np.max(np.abs(rust_result))) <= 1.0
    assert np.allclose(numpy_result, rust_result, atol=1e-5, rtol=1e-5)


def test_dsp_rejects_non_finite_input():
    dsp = RustDSP()
    with pytest.raises(ValueError, match="non_finite_audio"):
        dsp.soft_clip(np.array([0.0, np.inf], dtype=np.float32))
