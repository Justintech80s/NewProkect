from app.services.worker_performance import WorkerPerformanceStore


def test_unconfigured_store_returns_empty(monkeypatch):
    monkeypatch.delenv("JUST_MAKER_DATABASE_URL", raising=False)
    store = WorkerPerformanceStore()
    assert store.summary() == {}


def test_bonus_is_zero_without_enough_history(monkeypatch):
    store = WorkerPerformanceStore()
    monkeypatch.setattr(store, "summary", lambda: {
        "gpu-a": {
            "evaluations": 2,
            "average_score": 0.95,
            "pass_rate": 1.0,
            "eligible": False,
        }
    })
    result = store.routing_bonus("gpu-a")
    assert result["bonus"] == 0.0


def test_bonus_rewards_proven_worker(monkeypatch):
    store = WorkerPerformanceStore()
    monkeypatch.setattr(store, "summary", lambda: {
        "gpu-a": {
            "evaluations": 20,
            "average_score": 0.9,
            "pass_rate": 0.85,
            "eligible": True,
        }
    })
    result = store.routing_bonus("gpu-a")
    assert 0.0 < result["bonus"] <= 0.12
