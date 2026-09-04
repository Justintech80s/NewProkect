from pathlib import Path
import wave

from app.services.procedural import ProceduralMusicProvider


def test_procedural_provider_renders_valid_wav():
    provider = ProceduralMusicProvider()
    result = provider.generate(
        {
            "bpm": 100,
            "key": "C minor",
            "duration_seconds": 10,
            "drums": {"density": "sparse"},
        }
    )

    path = Path(result["audio_path"])
    assert path.exists()
    assert path.stat().st_size > 1000

    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 22050
        assert wf.getnframes() > 0
