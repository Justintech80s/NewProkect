from app.services.creative_memory import CreativeMemoryStore


def test_creative_memory_noops_without_user():
    store = CreativeMemoryStore()
    plan = {"producer_dna": {"bass_prominence": 0.5}}
    assert store.apply(None, plan) == plan


def test_creative_memory_blends_successful_traits(monkeypatch):
    store = CreativeMemoryStore()
    monkeypatch.setattr(
        store,
        "best",
        lambda user_id, limit=3: [
            {
                "job_id": "a",
                "score": 0.95,
                "recipe": {"producer_dna": {"bass_prominence": 1.0}},
            },
            {
                "job_id": "b",
                "score": 0.90,
                "recipe": {"producer_dna": {"bass_prominence": 0.9}},
            },
        ],
    )
    result = store.apply(
        "00000000-0000-0000-0000-000000000001",
        {"producer_dna": {"bass_prominence": 0.5}},
    )
    assert result["producer_dna"]["bass_prominence"] > 0.5
    assert result["producer_dna"]["creative_memory_applied"] is True
    assert result["creative_memory"]["source_jobs"] == ["a", "b"]


def test_clean_dna_excludes_direct_copy_fields():
    store = CreativeMemoryStore()
    cleaned = store._clean_dna({
        "bass_prominence": 0.8,
        "note_sequence": [60, 62],
        "exact_arrangement": "copy",
    })
    assert cleaned == {"bass_prominence": 0.8}
