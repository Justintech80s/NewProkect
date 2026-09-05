from app.music_brain.audio_intelligence import AudioIntelligenceEngine


def test_uncleared_audio_is_not_indexed():
    engine = AudioIntelligenceEngine()
    result = engine.index_sample_asset(
        sample_asset_id=1,
        audio_path="/does/not/matter.wav",
        rights_status="copyrighted",
        sampling_allowed=False,
        commercial_use=False,
    )
    assert result["indexed"] is False
    assert result["reason"] == "audio_not_cleared_for_automatic_analysis"


def test_unknown_audio_is_not_indexed():
    engine = AudioIntelligenceEngine()
    result = engine.index_sample_asset(
        sample_asset_id=1,
        audio_path="/does/not/matter.wav",
        rights_status="unknown",
        sampling_allowed=False,
        commercial_use=False,
    )
    assert result["indexed"] is False
