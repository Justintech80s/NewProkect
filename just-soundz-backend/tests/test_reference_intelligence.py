import wave

import numpy as np

from app.services.originality_guard import OriginalityGuard
from app.services.reference_audio import ReferenceAudioAnalyzer
from app.services.reference_traits import ReferenceTraitBlender


def _write_wav(path, sr=8000):
    t = np.arange(sr * 2, dtype=np.float32) / sr
    audio = (
        0.22 * np.sin(2 * np.pi * 90 * t)
        + 0.08 * np.sin(2 * np.pi * 1200 * t)
    )
    pcm = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def test_reference_analyzer_extracts_traits_without_melody(tmp_path):
    path = tmp_path / "reference.wav"
    _write_wav(path)

    result = ReferenceAudioAnalyzer().analyze(str(path))

    assert "production_traits" in result
    assert result["policy"]["melody_extracted"] is False
    assert result["policy"]["production_traits_only"] is True


def test_reference_traits_blend_into_producer_dna():
    plan = {
        "producer_dna": {
            "bass_prominence": 0.5,
            "percussion_complexity": 0.5,
            "mix_polish": 0.5,
            "negative_space": 0.5,
        },
        "reference_audio": {
            "production_traits": {
                "low_end_weight": 1.0,
                "rhythmic_density": 0.8,
                "mix_polish_hint": 0.9,
                "transient_punch": 0.7,
                "brightness": 0.4,
                "dynamic_range": 0.6,
            }
        },
    }

    result = ReferenceTraitBlender().apply(plan)

    assert result["producer_dna"]["bass_prominence"] > 0.5
    assert result["producer_dna"]["reference_trait_blend"] is True


def test_originality_guard_rejects_direct_note_sequence():
    guard = OriginalityGuard()
    plan = {
        "reference_audio": {
            "note_sequence": [60, 64, 67],
            "policy": {
                "melody_extracted": False,
                "note_sequence_stored": False,
            },
        }
    }

    result = guard.evaluate(plan)
    assert result["pass"] is False
    assert "note_sequence" in result["violations"]
