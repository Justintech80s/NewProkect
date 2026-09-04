from app.services.harmony_planner import HarmonyPlanner
from app.services.instrumentation_planner import InstrumentationPlanner
from app.services.producer_dna import ProducerDNAEngine
from app.services.rhythm_transformer import RhythmTransformer


def test_syncopated_profile_builds_distinct_rhythm_plan():
    plan = {
        "bpm": 102,
        "key": "F# minor",
        "mood": ["dark"],
        "production_context": {"genres": ["hip hop"], "instruments": []},
    }

    dna_engine = ProducerDNAEngine()
    rhythm = RhythmTransformer()
    harmony = HarmonyPlanner()
    instrumentation = InstrumentationPlanner()

    plan = dna_engine.apply("futuristic unusual percussion with negative space", plan)
    plan = rhythm.apply(plan)
    plan = harmony.apply(plan)
    plan = instrumentation.apply(plan)

    assert plan["producer_dna"]["archetype"] == "syncopated_futurist"
    assert plan["producer_dna"]["syncopation"] > 0.8
    assert len(plan["rhythm_plan"]["percussion"]) >= 4
    assert plan["harmony_plan"]["key"] == "F# minor"
    assert "unusual percussion" in plan["instrumentation_plan"]["primary"]


def test_gritty_sample_profile_uses_high_chop_intensity():
    engine = ProducerDNAEngine()
    plan = engine.apply(
        "gritty dusty cinematic sample based beat",
        {"bpm": 90, "key": "C minor", "production_context": {}},
    )
    assert plan["producer_dna"]["archetype"] == "gritty_cinematic_sampler"
    assert plan["producer_dna"]["sample_chop_intensity"] >= 0.85


def test_west_coast_profile_prioritizes_bass_and_polish():
    engine = ProducerDNAEngine()
    plan = engine.apply(
        "polished west coast synth bass hip hop",
        {"bpm": 94, "key": "D minor", "production_context": {}},
    )
    dna = plan["producer_dna"]
    assert dna["archetype"] == "polished_west_coast"
    assert dna["bass_prominence"] > 0.8
    assert dna["mix_polish"] > 0.9
