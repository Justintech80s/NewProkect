from app.services.worker_performance import WorkerPerformanceStore


def test_context_key_separates_genre_duration_and_mix_mode():
    store = WorkerPerformanceStore()
    plan = {
        "duration_seconds": 300,
        "production_context": {"genres": ["Hip Hop"]},
        "conditioning": {"stems": True},
    }
    assert store.context_key(plan) == "hip hop:long:stems"


def test_context_key_has_safe_defaults():
    store = WorkerPerformanceStore()
    assert store.context_key({"duration_seconds": 60}) == "general:short:mix"
