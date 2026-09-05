from __future__ import annotations

import os
from typing import Any, Dict


class AdaptiveCacheTuner:
    """Chooses conservative TTLs from observed cache efficiency and churn."""

    def __init__(self):
        self.enabled = os.getenv("JUST_MAKER_ADAPTIVE_CACHE_TTL", "1").lower() in {
            "1", "true", "yes", "on"
        }
        self.min_ttl = int(os.getenv("JUST_MAKER_CACHE_MIN_TTL_SECONDS", "120"))
        self.max_ttl = int(os.getenv("JUST_MAKER_CACHE_MAX_TTL_SECONDS", "3600"))
        self.default_ttl = int(os.getenv("JUST_MAKER_ROCKSDB_TTL_SECONDS", "900"))

    def recommend(
        self,
        metrics: Dict[str, Any],
        *,
        namespace: str,
        base_ttl: int | None = None,
    ) -> Dict[str, Any]:
        base = int(base_ttl or self.default_ttl)
        if not self.enabled:
            return {
                "enabled": False,
                "namespace": namespace,
                "recommended_ttl_seconds": base,
                "reason": "adaptive_tuning_disabled",
            }

        hits = int(metrics.get("hits") or 0)
        misses = int(metrics.get("misses") or 0)
        invalidated = int(metrics.get("invalidated") or 0)
        errors = int(metrics.get("errors") or 0)
        lookups = hits + misses
        hit_rate = hits / lookups if lookups else 0.0
        churn = invalidated / max(1, int(metrics.get("writes") or 0))

        ttl = base
        reasons = []

        if lookups < 20:
            reasons.append("insufficient_observations")
        else:
            if hit_rate >= 0.75 and churn < 0.25:
                ttl = int(base * 1.5)
                reasons.append("high_hit_rate_low_churn")
            elif hit_rate <= 0.30:
                ttl = int(base * 0.65)
                reasons.append("low_hit_rate")
            if churn >= 0.75:
                ttl = int(ttl * 0.6)
                reasons.append("high_invalidation_churn")
            if errors > max(2, lookups * 0.05):
                ttl = min(ttl, base)
                reasons.append("cache_error_guard")

        ttl = max(self.min_ttl, min(self.max_ttl, ttl))
        return {
            "enabled": True,
            "namespace": namespace,
            "recommended_ttl_seconds": ttl,
            "base_ttl_seconds": base,
            "hit_rate": round(hit_rate, 4),
            "invalidation_churn": round(churn, 4),
            "observations": lookups,
            "reasons": reasons or ["steady_state"],
        }

    def ttl_for(self, cache) -> int:
        recommendation = self.recommend(
            cache.metrics(),
            namespace=cache.namespace,
            base_ttl=cache.default_ttl,
        )
        return int(recommendation["recommended_ttl_seconds"])
