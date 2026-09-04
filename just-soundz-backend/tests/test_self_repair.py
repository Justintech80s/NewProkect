from app.services.self_repair import SelfRepairEngine


def test_repair_strengthens_tempo_and_key_conditioning():
    engine = SelfRepairEngine()
    plan = {
        "bpm": 94,
        "key": "C minor",
        "rhythm_plan": {},
        "harmony_plan": {},
        "conditioning": {"musical": {}},
        "arrangement": [],
        "producer_dna": {},
        "negative_instructions": [],
    }

    repaired = engine.apply(
        plan,
        {
            "score": 0.55,
            "issues": ["tempo_mismatch", "key_mismatch"],
        },
        attempt=1,
    )

    assert repaired["rhythm_plan"]["tempo_lock"] is True
    assert repaired["conditioning"]["musical"]["bpm"] == 94
    assert repaired["harmony_plan"]["key"] == "C minor"
    assert repaired["harmony_plan"]["tonic_emphasis"] > 0.8


def test_repair_increases_section_variation():
    engine = SelfRepairEngine()
    plan = {
        "arrangement": [
            {"section": "verse", "energy": 0.55, "variation": 0},
            {"section": "hook", "energy": 0.95, "variation": 1},
        ],
        "producer_dna": {
            "negative_space": 0.5,
            "arrangement_density": 0.5,
        },
        "rhythm_plan": {},
        "negative_instructions": [],
    }

    repaired = engine.apply(
        plan,
        {"score": 0.60, "issues": ["excessive_repetition"]},
        attempt=1,
    )

    assert repaired["arrangement"][0]["variation"] > 0
    assert repaired["rhythm_plan"]["force_pattern_mutation"] is True
    assert repaired["producer_dna"]["negative_space"] > 0.5
