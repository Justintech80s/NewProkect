from app.music_brain.embeddings import MusicEmbeddingEngine
from app.music_brain.rights import SampleRightsEngine


def test_embedding_fallback_is_stable_and_normalized():
    engine = MusicEmbeddingEngine()
    a = engine.text_embedding("dark dusty soul 92 bpm")
    b = engine.text_embedding("dark dusty soul 92 bpm")
    assert len(a) == 512
    assert a == b


def test_rights_engine_blocks_unknown_audio():
    engine = SampleRightsEngine()
    result = engine.evaluate({
        "status": "unknown",
        "commercial_use": False,
        "sampling_allowed": False,
    })
    assert result["eligible_for_automatic_sampling"] is False
    assert result["reference_only"] is True


def test_rights_engine_allows_cleared_audio():
    engine = SampleRightsEngine()
    result = engine.evaluate({
        "status": "licensed",
        "commercial_use": True,
        "sampling_allowed": True,
    })
    assert result["eligible_for_automatic_sampling"] is True
