from app.services.producer_dna import ProducerDNAEngine


def test_kanye_reference_becomes_broad_soul_chop_controls():
    engine = ProducerDNAEngine()
    plan = {"bpm": 92, "key": "C minor", "production_context": {}}
    profile = engine.build_profile("make a Kanye West type beat", plan)
    assert profile["archetype"] == "soul_chop_maximalist"
    assert profile["sample_chop_intensity"] >= 0.8
    assert profile["identity_policy"]["named_reference_translated_to_traits"] is True
    assert profile["identity_policy"]["melody_copy"] is False
    assert profile["identity_policy"]["copyrighted_sample_auto_use"] is False


def test_industrial_era_reference_maps_to_electronic_controls():
    engine = ProducerDNAEngine()
    plan = {"bpm": 120, "key": "A minor", "production_context": {}}
    profile = engine.build_profile("Kanye Yeezus industrial beat", plan)
    assert profile["archetype"] == "electro_minimalist"
    assert profile["negative_space"] >= 0.75
