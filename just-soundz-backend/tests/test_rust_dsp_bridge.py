import numpy as np

from app.services.rust_dsp import RustDSP


def test_rust_dsp_falls_back_when_extension_is_missing(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_RUST_DSP_ENABLED", "0")
    dsp = RustDSP()
    assert dsp.available is False
    assert dsp.status()["engine"] == "numpy-fallback"


def test_rust_dsp_fallback_normalizes_peak(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_RUST_DSP_ENABLED", "0")
    dsp = RustDSP()
    audio = np.array([[0.2], [-0.4], [0.1]], dtype=np.float32)
    out = dsp.normalize_peak(audio, -1.0)
    assert np.max(np.abs(out)) < 1.0
    assert np.max(np.abs(out)) > 0.85


def test_rust_dsp_fallback_removes_dc(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_RUST_DSP_ENABLED", "0")
    dsp = RustDSP()
    audio = np.full((100, 2), 0.25, dtype=np.float32)
    out = dsp.remove_dc(audio)
    assert abs(float(np.mean(out))) < 1e-6
