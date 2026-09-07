from __future__ import annotations

from app.services.model_registry import WorkerConfig
from app.services.capabilities import WorkerCapabilities
from app.services.orchestration import OrchestrationPolicy
from app.services.router import GenerationRouter


def worker(name: str) -> WorkerConfig:
    return WorkerConfig(
        name=name,
        kind="http-worker",
        url=f"https://{name}.invalid",
        token=None,
        priority=10,
        capabilities=WorkerCapabilities(
            text_prompt=True,
            bpm=True,
            key=True,
            rhythm_conditioning=True,
            harmony_conditioning=True,
            instrumentation_conditioning=True,
            arrangement_conditioning=True,
            stem_conditioning=True,
            sample_conditioning=True,
            negative_prompt=True,
            max_duration_seconds=600,
        ),
    )


class FakeSelector:
    def __init__(self, names):
        self._workers = [worker(name) for name in names]

    def rank(self, plan):
        return [
            (
                item,
                {
                    "score": 1.0,
                    "coverage": 1.0,
                    "duration_ok": True,
                    "routing_context": "fixture",
                    "historical_bonus": 0.0,
                    "global_performance": {},
                    "contextual_performance": {},
                },
            )
            for item in self._workers
        ]


class FakeCircuit:
    def allow(self, _name):
        return True

    def success(self, _name):
        return None

    def failure(self, _name):
        return None

    def status(self):
        return {}


class FakeProvider:
    def __init__(self, *, healthy=True, succeeds=False):
        self.healthy = healthy
        self.succeeds = succeeds

    def health(self, timeout_seconds=2.5):
        return {"ok": self.healthy, "timeout_seconds": timeout_seconds}

    def generate(self, plan, variation=0):
        if not self.succeeds:
            raise RuntimeError("generation failed")
        return {
            "provider": "fake",
            "audio_path": "/tmp/generated.wav",
            "audio_url": None,
            "metadata": {},
        }


def test_policy_bounds_environment(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_MAX_WORKER_ATTEMPTS", "999")
    monkeypatch.setenv("JUST_MAKER_WORKER_HEALTH_TIMEOUT_SECONDS", "999")
    monkeypatch.setenv("JUST_MAKER_RETRYABLE_FAILURES", "999")
    policy = OrchestrationPolicy.from_env()
    assert policy.max_worker_attempts == 12
    assert policy.health_timeout_seconds == 30.0
    assert policy.retryable_failures == 5


def test_router_skips_unhealthy_worker_and_fails_over(monkeypatch):
    router = GenerationRouter()
    router.selector = FakeSelector(["bad", "good"])
    router.circuit_breaker = FakeCircuit()
    router.policy = OrchestrationPolicy(
        max_worker_attempts=4,
        health_timeout_seconds=1.0,
        retryable_failures=1,
    )

    providers = {
        "bad": FakeProvider(healthy=False, succeeds=False),
        "good": FakeProvider(healthy=True, succeeds=True),
    }
    monkeypatch.setattr(router, "_provider_for", lambda config: providers[config.name])

    result = router.generate({"duration_seconds": 30}, variation=0)
    assert result["audio_path"] == "/tmp/generated.wav"
    assert result["routing"]["selected_worker"] == "good"
    assert result["routing"]["orchestration"]["policy"] == "pass5-v1"
    assert result["routing"]["attempts"][0]["reason"] == "health_check_failed"


def test_router_enforces_worker_attempt_budget(monkeypatch):
    router = GenerationRouter()
    router.selector = FakeSelector(["a", "b", "c"])
    router.circuit_breaker = FakeCircuit()
    router.policy = OrchestrationPolicy(
        max_worker_attempts=1,
        health_timeout_seconds=1.0,
        retryable_failures=0,
    )
    monkeypatch.setattr(
        router,
        "_provider_for",
        lambda config: FakeProvider(healthy=True, succeeds=False),
    )

    result = router.generate({"duration_seconds": 30}, variation=0)
    assert result["provider"] == "unavailable"
    assert result["routing"]["orchestration"]["attempted"] == 1
    assert any(
        item.get("reason") == "attempt_budget_exhausted"
        for item in result["routing"]["attempts"]
    )
