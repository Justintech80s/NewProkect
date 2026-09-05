from app.main import GenerateRequest
from app.services.novelty_engine import NoveltyEngine


def test_generate_request_accepts_variation_zero_to_five():
    assert GenerateRequest(prompt="make a soulful instrumental", variation=5).variation == 5


def test_variation_number_changes_novelty_recipe():
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
    first = engine.apply(plan, "soulful instrumental", variation=0)
    second = engine.apply(plan, "soulful instrumental", variation=1)
    assert first["novelty"] != second["novelty"]


def test_same_variation_is_reproducible():
    engine = NoveltyEngine()
    plan = {"producer_dna": {"swing": 0.5, "syncopation": 0.5}}
    a = engine.apply(plan, "dark drums", variation=3)
    b = engine.apply(plan, "dark drums", variation=3)
    assert a["producer_dna"] == b["producer_dna"]
