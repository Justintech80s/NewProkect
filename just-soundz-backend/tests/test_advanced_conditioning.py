from app.services.advanced_conditioning import AdvancedConditioningPlanner


def test_advanced_conditioning_builds_time_aligned_controls():
    plan = {
        "bpm": 120,
        "key": "C minor",
        "arrangement": [
            {"section": "verse", "bars": 4, "energy": 0.5},
            {"section": "hook", "bars": 4, "energy": 0.9},
        ],
        "rhythm_plan": {
            "grid": "16-step",
            "swing": 0.56,
            "kick": [{"step": 0, "velocity": 1.0}],
            "snare": [{"step": 4, "velocity": 0.95}],
            "hats": {"steps": [0, 2, 4, 6], "swing": 0.56},
            "percussion": [3, 11],
        },
        "harmony_plan": {
            "progression": ["i", "VI", "III", "VII"],
        },
        "instrumentation_plan": {
            "primary": ["drums", "bass"],
            "secondary": ["keys"],
        },
        "producer_dna": {
            "arrangement_density": 0.6,
            "swing": 0.56,
        },
    }

    controls = AdvancedConditioningPlanner().build(plan)

    assert controls["tempo"]["seconds_per_beat"] == 0.5
    assert controls["sections"][0]["start_seconds"] == 0.0
    assert controls["sections"][0]["end_seconds"] == 8.0
    assert len(controls["chords"]) == 8
    assert controls["rhythm"]["snare"][0]["offset_seconds"] == 0.5
    assert controls["originality"]["direct_melodic_copying"] is False
