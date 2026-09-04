from app.services.conditioning import ConditioningCompiler
from app.services.production_critic import ProductionCritic
from app.services.stem_arranger import StemArranger


def test_stem_arranger_builds_section_and_bus_plan():
    plan = {
        "producer_dna": {
            "bass_prominence": 0.9,
            "mix_polish": 0.9,
            "arrangement_density": 0.6,
            "lofi_character": 0.2,
        },
        "instrumentation_plan": {"primary": ["bass", "keys"]},
        "arrangement": [
            {"section": "verse", "bars": 16, "energy": 0.55},
            {"section": "hook", "bars": 8, "energy": 0.95},
        ],
    }
    out = StemArranger().build(plan)
    assert "bass" in out["stems"]
    assert "lead" in out["sections"][1]["active_stems"]


def test_conditioning_compiler_collects_major_plans():
    plan = {
        "original_prompt": "dark hip hop instrumental",
        "bpm": 94,
        "key": "C minor",
        "duration_seconds": 120,
        "producer_dna": {"archetype": "gritty_cinematic_sampler", "swing": 0.57},
        "rhythm_plan": {"grid": "16-step"},
        "harmony_plan": {"progression": ["i", "VI", "III", "VII"]},
        "instrumentation_plan": {"primary": ["dusty drums"]},
        "arrangement": [{"section": "verse", "bars": 16}],
        "stem_arrangement": {"stems": {"drums": {}}},
        "sample_brain": {"policy": "rights-cleared-only", "processed_samples": []},
        "music_brain": {"guidance": {}, "reference_count": 5},
        "negative_instructions": [],
    }
    conditioning = ConditioningCompiler().compile(plan)
    assert conditioning["musical"]["bpm"] == 94
    assert conditioning["production"]["archetype"] == "gritty_cinematic_sampler"


def test_production_critic_passes_well_aligned_render():
    plan = {
        "bpm": 94,
        "key": "C minor",
        "producer_dna": {
            "swing": 0.55, "syncopation": 0.6, "negative_space": 0.5,
            "kick_density": 0.3, "bass_prominence": 0.8,
            "sample_chop_intensity": 0.6, "mix_polish": 0.9,
        },
        "conditioning": {
            "text": {"prompt": "x"},
            "musical": {"bpm": 94},
            "rhythm": {"grid": "16-step"},
            "production": {"archetype": "modern_minimal"},
            "instrumentation": {"primary": ["bass"]},
            "arrangement": [{"section": "verse"}],
        },
    }
    critique = ProductionCritic().evaluate(
        plan,
        {"bpm": 94, "key": "C"},
        {"score": 0.70, "too_repetitive": False},
        {"mastered": True, "peak_dbfs": -1.0},
    )
    assert critique["pass"] is True
    assert critique["score"] >= 0.72
