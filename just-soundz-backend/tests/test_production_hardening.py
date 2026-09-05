from app.services.circuit_breaker import WorkerCircuitBreaker
from app.services.operations import OperationsMetrics


def test_circuit_breaker_opens_after_threshold(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_CIRCUIT_FAILURE_THRESHOLD", "2")
    breaker = WorkerCircuitBreaker()
    assert breaker.allow("gpu") is True
    breaker.failure("gpu")
    assert breaker.allow("gpu") is True
    breaker.failure("gpu")
    assert breaker.allow("gpu") is False


def test_cost_estimate_scales_with_stems(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_GPU_COST_PER_SECOND", "0.001")
    metrics = OperationsMetrics()
    assert metrics.estimate_generation_cost(60, attempts=2, stem_count=3) == 0.36
