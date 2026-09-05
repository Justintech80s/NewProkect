from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .capabilities import WorkerCapabilities


@dataclass
class WorkerConfig:
    name: str
    kind: str
    url: Optional[str]
    token: Optional[str]
    priority: int
    capabilities: WorkerCapabilities

    def public_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "configured": bool(self.url) or self.kind == "built-in-procedural",
            "priority": self.priority,
            "capabilities": self.capabilities.to_dict(),
        }


class ModelRegistry:
    """Environment-driven registry of available generation workers."""

    def workers(self) -> List[WorkerConfig]:
        workers: List[WorkerConfig] = []

        workers.append(WorkerConfig(
            name="built-in-procedural",
            kind="built-in-procedural",
            url=None,
            token=None,
            priority=1000,
            capabilities=WorkerCapabilities(
                text_prompt=True,
                bpm=True,
                key=True,
                rhythm_conditioning=False,
                harmony_conditioning=False,
                instrumentation_conditioning=False,
                arrangement_conditioning=False,
                stem_conditioning=False,
                sample_conditioning=False,
                negative_prompt=False,
                max_duration_seconds=180,
            ),
        ))

        specs = [
            ("primary-gpu", "http-worker", "JUST_SOUNDZ_PRIMARY_WORKER_URL", "JUST_SOUNDZ_PRIMARY_WORKER_TOKEN", 10),
            ("musicgen-jasco", "musicgen-jasco-worker", "JUST_SOUNDZ_MUSICGEN_WORKER_URL", "JUST_SOUNDZ_MUSICGEN_WORKER_TOKEN", 20),
            ("stable-audio", "stable-audio-worker", "JUST_SOUNDZ_STABLE_WORKER_URL", "JUST_SOUNDZ_STABLE_WORKER_TOKEN", 30),
        ]
        specs.extend(self._ensemble_specs())

        for name, kind, url_key, token_key, priority in specs:
            url = os.getenv(url_key)
            if not url:
                continue

            workers.append(WorkerConfig(
                name=name,
                kind=kind,
                url=url,
                token=os.getenv(token_key),
                priority=priority,
                capabilities=self._capabilities_from_env(name, kind),
            ))

        return sorted(workers, key=lambda w: w.priority)

    def _ensemble_specs(self):
        """Adds arbitrary licensed GPU/model workers without code changes.

        Format:
        name|kind|url_env|token_env|priority;...
        """
        raw = os.getenv("JUST_MAKER_ENSEMBLE_WORKERS", "").strip()
        specs = []
        if not raw:
            return specs
        for item in raw.split(";"):
            parts = [part.strip() for part in item.split("|")]
            if len(parts) != 5:
                continue
            name, kind, url_key, token_key, priority = parts
            if kind not in {
                "http-worker",
                "musicgen-jasco-worker",
                "stable-audio-worker",
            }:
                continue
            try:
                priority_value = int(priority)
            except ValueError:
                continue
            specs.append((name, kind, url_key, token_key, priority_value))
        return specs

    def _capabilities_from_env(self, name: str, kind: str) -> WorkerCapabilities:
        prefix = name.upper().replace("-", "_")
        default = self._defaults(kind)

        def flag(field: str, current: bool) -> bool:
            raw = os.getenv(f"JUST_SOUNDZ_{prefix}_{field.upper()}")
            if raw is None:
                return current
            return raw.strip().lower() in {"1", "true", "yes", "on"}

        max_duration = int(
            os.getenv(
                f"JUST_SOUNDZ_{prefix}_MAX_DURATION_SECONDS",
                str(default.max_duration_seconds),
            )
        )

        return WorkerCapabilities(
            text_prompt=flag("text_prompt", default.text_prompt),
            bpm=flag("bpm", default.bpm),
            key=flag("key", default.key),
            rhythm_conditioning=flag("rhythm_conditioning", default.rhythm_conditioning),
            harmony_conditioning=flag("harmony_conditioning", default.harmony_conditioning),
            instrumentation_conditioning=flag("instrumentation_conditioning", default.instrumentation_conditioning),
            arrangement_conditioning=flag("arrangement_conditioning", default.arrangement_conditioning),
            stem_conditioning=flag("stem_conditioning", default.stem_conditioning),
            sample_conditioning=flag("sample_conditioning", default.sample_conditioning),
            negative_prompt=flag("negative_prompt", default.negative_prompt),
            max_duration_seconds=max_duration,
        )

    def _defaults(self, kind: str) -> WorkerCapabilities:
        if kind == "musicgen-jasco-worker":
            return WorkerCapabilities(
                text_prompt=True, bpm=True, key=True,
                rhythm_conditioning=True, harmony_conditioning=True,
                instrumentation_conditioning=True, arrangement_conditioning=True,
                stem_conditioning=False, sample_conditioning=True,
                negative_prompt=False, max_duration_seconds=240,
            )
        if kind == "stable-audio-worker":
            return WorkerCapabilities(
                text_prompt=True, bpm=False, key=False,
                rhythm_conditioning=False, harmony_conditioning=False,
                instrumentation_conditioning=True, arrangement_conditioning=False,
                stem_conditioning=False, sample_conditioning=False,
                negative_prompt=True, max_duration_seconds=180,
            )
        return WorkerCapabilities(
            text_prompt=True, bpm=True, key=True,
            rhythm_conditioning=True, harmony_conditioning=True,
            instrumentation_conditioning=True, arrangement_conditioning=True,
            stem_conditioning=True, sample_conditioning=True,
            negative_prompt=True, max_duration_seconds=600,
        )
