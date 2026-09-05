from app.services.preferences import PreferenceLearningStore


def test_personalization_noops_without_user():
    store = PreferenceLearningStore()
    plan = {"producer_dna": {"bass_prominence": 0.5}}
    assert store.apply_to_plan(None, plan) == plan


def test_personalization_blends_preferences(monkeypatch):
    store = PreferenceLearningStore()

    monkeypatch.setattr(
        store,
        "get_profile",
        lambda user_id: {
            "configured": True,
            "traits": {"bass_prominence": 1.0, "mix_polish": 0.9},
            "feedback_count": 12,
        },
    )

    plan = {
        "producer_dna": {
            "bass_prominence": 0.5,
            "mix_polish": 0.5,
        }
    }

    result = store.apply_to_plan(
        "00000000-0000-0000-0000-000000000001",
        plan,
    )

    assert result["producer_dna"]["bass_prominence"] > 0.5
    assert result["producer_dna"]["mix_polish"] > 0.5
    assert result["producer_dna"]["personalization_applied"] is True
