from __future__ import annotations

import time
from typing import Any, Dict, List

from .circuit_breaker import WorkerCircuitBreaker
from .model_registry import WorkerConfig
from .orchestration import OrchestrationPolicy
from .procedural import ProceduralMusicProvider
from .providers import (
    MusicGenJascoProvider,
    RemoteWorkerProvider,
    ReplicateDeploymentProvider,
    StableAudioProvider,
)
from .worker_selector import WorkerSelector


class GenerationRouter:
    """Capability-aware generation router with bounded health-aware failover."""

    def __init__(self):
        self.selector = WorkerSelector()
        self.circuit_breaker = WorkerCircuitBreaker()
        self.policy = OrchestrationPolicy.from_env()

    @property
    def provider(self) -> str:
        workers = self.selector.registry.workers()
        if not workers:
            return "unavailable"
        return workers[0].name

    def generate(self, plan: Dict[str, Any], variation: int = 0):
        attempts: List[Dict[str, Any]] = []
        started_at = time.time()

        for worker, ranking in self.selector.rank(plan):
            if not self.policy.should_attempt(attempts):
                attempts.append({
                    "worker": worker.name,
                    "status": "skipped",
                    "reason": "attempt_budget_exhausted",
                    **ranking,
                })
                break

            if not self.circuit_breaker.allow(worker.name):
                attempts.append({
                    "worker": worker.name,
                    "status": "skipped",
                    "reason": "circuit_open",
                    **ranking,
                })
                continue

            if not ranking.get("duration_ok"):
                attempts.append({
                    "worker": worker.name,
                    "status": "skipped",
                    "reason": "duration_exceeds_worker_limit",
                    **ranking,
                })
                continue

            provider = self._provider_for(worker)
            if provider is None:
                attempts.append({
                    "worker": worker.name,
                    "status": "skipped",
                    "reason": "provider_unavailable",
                    **ranking,
                })
                continue

            health = self._health(provider)
            if not health.get("ok", False):
                self.circuit_breaker.failure(worker.name)
                attempts.append({
                    "worker": worker.name,
                    "status": "skipped",
                    "reason": "health_check_failed",
                    "health": health,
                    **ranking,
                })
                continue

            try:
                result = provider.generate(plan, variation)
                if result.get("audio_path") or result.get("audio_url"):
                    self.circuit_breaker.success(worker.name)
                    attempts.append({
                        "worker": worker.name,
                        "status": "success",
                        "health": health,
                        **ranking,
                    })
                    result["routing"] = {
                        "selected_worker": worker.name,
                        "selected_kind": worker.kind,
                        "coverage": ranking.get("coverage"),
                        "score": ranking.get("score"),
                        "routing_context": ranking.get("routing_context"),
                        "historical_bonus": ranking.get("historical_bonus"),
                        "global_performance": ranking.get("global_performance"),
                        "contextual_performance": ranking.get("contextual_performance"),
                        "attempts": attempts,
                        "orchestration": self.policy.audit(
                            attempts,
                            started_at=started_at,
                        ),
                    }
                    return result

                self.circuit_breaker.failure(worker.name)
                attempts.append({
                    "worker": worker.name,
                    "status": "failed",
                    "reason": "no_audio_returned",
                    "health": health,
                    **ranking,
                })
            except Exception as exc:
                self.circuit_breaker.failure(worker.name)
                attempts.append({
                    "worker": worker.name,
                    "status": "failed",
                    "reason": exc.__class__.__name__,
                    "health": health,
                    **ranking,
                })

        return {
            "provider": "unavailable",
            "audio_path": None,
            "audio_url": None,
            "message": "No configured generation worker produced audio.",
            "routing": {
                "selected_worker": None,
                "attempts": attempts,
                "orchestration": self.policy.audit(
                    attempts,
                    started_at=started_at,
                ),
            },
        }

    def status(self, plan: Dict[str, Any] | None = None) -> Dict[str, Any]:
        workers = []
        if plan is None:
            for worker in self.selector.registry.workers():
                workers.append(worker.public_dict())
        else:
            for worker, ranking in self.selector.rank(plan):
                workers.append({
                    **worker.public_dict(),
                    "ranking": ranking,
                })
        return {
            "workers": workers,
            "circuits": self.circuit_breaker.status(),
            "orchestration_policy": {
                "version": "pass5-v1",
                "max_worker_attempts": self.policy.max_worker_attempts,
                "health_timeout_seconds": self.policy.health_timeout_seconds,
                "retryable_failures": self.policy.retryable_failures,
            },
        }

    def _health(self, provider) -> Dict[str, Any]:
        health = getattr(provider, "health", None)
        if health is None:
            return {"ok": True, "mode": "local"}
        try:
            result = health(timeout_seconds=self.policy.health_timeout_seconds)
            return result if isinstance(result, dict) else {"ok": bool(result)}
        except Exception as exc:
            return {"ok": False, "reason": exc.__class__.__name__}

    def _provider_for(self, worker: WorkerConfig):
        if worker.kind == "built-in-procedural":
            return ProceduralMusicProvider()
        if worker.kind == "replicate-deployment":
            return ReplicateDeploymentProvider(worker.url or "", worker.token)
        if worker.kind == "http-worker":
            return RemoteWorkerProvider(worker.url or "", worker.token)
        if worker.kind == "musicgen-jasco-worker":
            return MusicGenJascoProvider(worker.url or "", worker.token)
        if worker.kind == "stable-audio-worker":
            return StableAudioProvider(worker.url or "", worker.token)
        return None
