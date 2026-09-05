from __future__ import annotations

from typing import Any, Dict, List

from .circuit_breaker import WorkerCircuitBreaker
from .model_registry import WorkerConfig
from .procedural import ProceduralMusicProvider
from .providers import (
    MusicGenJascoProvider,
    RemoteWorkerProvider,
    StableAudioProvider,
)
from .worker_selector import WorkerSelector


class GenerationRouter:
    """Capability-aware generation router with ordered failover."""

    def __init__(self):
        self.selector = WorkerSelector()
        self.circuit_breaker = WorkerCircuitBreaker()

    @property
    def provider(self) -> str:
        workers = self.selector.registry.workers()
        if not workers:
            return "unavailable"
        return workers[0].name

    def generate(self, plan: Dict[str, Any], variation: int = 0):
        attempts: List[Dict[str, Any]] = []

        for worker, ranking in self.selector.rank(plan):
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

            try:
                result = provider.generate(plan, variation)
                if result.get("audio_path") or result.get("audio_url"):
                    self.circuit_breaker.success(worker.name)
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
                    }
                    return result

                self.circuit_breaker.failure(worker.name)
                attempts.append({
                    "worker": worker.name,
                    "status": "failed",
                    "reason": "no_audio_returned",
                    **ranking,
                })
            except Exception as exc:
                self.circuit_breaker.failure(worker.name)
                attempts.append({
                    "worker": worker.name,
                    "status": "failed",
                    "reason": exc.__class__.__name__,
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
        }

    def _provider_for(self, worker: WorkerConfig):
        if worker.kind == "built-in-procedural":
            return ProceduralMusicProvider()
        if worker.kind == "http-worker":
            return RemoteWorkerProvider(worker.url or "", worker.token)
        if worker.kind == "musicgen-jasco-worker":
            return MusicGenJascoProvider(worker.url or "", worker.token)
        if worker.kind == "stable-audio-worker":
            return StableAudioProvider(worker.url or "", worker.token)
        return None
