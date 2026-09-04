import wave
from pathlib import Path

import numpy as np

from app.services.artifacts import ArtifactManifest


def test_artifact_manifest_hashes_audio(tmp_path):
    path = tmp_path / "track.wav"
    sr = 8000
    audio = (np.sin(2 * np.pi * 220 * np.arange(sr) / sr) * 10000).astype(np.int16)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio.tobytes())

    manifest = ArtifactManifest().from_path(
        str(path),
        artifact_type="master",
        job_id="11111111-1111-1111-1111-111111111111",
    )

    assert manifest["artifact_type"] == "master"
    assert manifest["size_bytes"] > 0
    assert len(manifest["sha256"]) == 64
