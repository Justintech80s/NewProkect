import wave
from pathlib import Path

import numpy as np

from app.services.sample_processor import SampleProcessor


def _write_test_wav(path: Path, sr: int = 8000):
    t = np.arange(sr, dtype=np.float32) / sr
    audio = 0.25 * np.sin(2 * np.pi * 220 * t)
    pcm = (audio * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def test_processor_transforms_cleared_local_wav(tmp_path):
    source = tmp_path / "sample.wav"
    _write_test_wav(source)

    processor = SampleProcessor()
    plan = {
        "sample_brain": {
            "selected": [{
                "id": 1,
                "sampling_allowed": True,
                "commercial_use": True,
                "rights_status": "licensed",
                "storage_uri": str(source),
                "transform": {"time_stretch_ratio": 1.25},
            }]
        }
    }

    result = processor.process_plan(plan)
    item = result["sample_brain"]["processed_samples"][0]

    assert item["status"] == "processed"
    assert Path(item["audio_path"]).exists()
    assert item["provenance"]["sampling_allowed"] is True


def test_processor_skips_uncleared_audio(tmp_path):
    source = tmp_path / "sample.wav"
    _write_test_wav(source)

    processor = SampleProcessor()
    plan = {
        "sample_brain": {
            "selected": [{
                "id": 1,
                "sampling_allowed": False,
                "storage_uri": str(source),
            }]
        }
    }

    result = processor.process_plan(plan)
    assert result["sample_brain"]["processed_samples"] == []
