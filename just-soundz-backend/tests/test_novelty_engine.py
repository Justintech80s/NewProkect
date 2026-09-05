from app.services.novelty_engine import NoveltyEngine


def test_novelty_is_deterministic_for_same_prompt_and_variation():
    engine = NoveltyEngine()
    plan = {"producer_dna": {
        "swing": 0.5,
        "syncopation": 0.5,
        "negative_space": 0.5,
        "percussion_complexity": 0.5,
        "harmonic_complexity": 0.5,
        "arrangement_density": 0.5,
        "sample_chop_intensity": 0.5,
    }}
    a = engine.apply(plan, "dark cinematic beat", 2)
    b = engine.apply(plan, "dark cinematic beat", 2)
    assert a["novelty"] == b["novelty"]
    assert a["producer_dna"] == b["producer_dna"]


def test_novelty_keeps_traits_bounded():
    engine = NoveltyEngine()
    result = engine.apply(
        {"producer_dna": {"swing": 0.99, "syncopation": 0.01}},
        "test",
        1,
    )
    assert 0.0 <= result["producer_dna"]["swing"] <= 1.0
    assert 0.0 <= result["producer_dna"]["syncopation"] <= 1.0


def test_candidate_variations_are_capped():
    assert NoveltyEngine().candidate_variations(99) == [0, 1, 2, 3, 4, 5]
