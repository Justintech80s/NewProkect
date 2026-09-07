from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Iterable, List, Sequence


class DatasetIntelligence:
    """Deterministic dataset confidence and retrieval-ranking contracts."""

    VERSION = "pass4-v1"
    MAX_GUIDANCE_ROWS = 50

    def normalize_tags(self, values: Iterable[Any], *, limit: int = 32) -> List[str]:
        seen = set()
        normalized: List[str] = []
        for raw in values or []:
            value = " ".join(str(raw).strip().lower().split())
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value[:80])
            if len(normalized) >= limit:
                break
        return normalized

    def validate_embedding(
        self,
        embedding: Sequence[float],
        *,
        expected_dimension: int,
    ) -> List[float]:
        if len(embedding) != expected_dimension:
            raise ValueError("invalid_embedding_dimension")
        values = [float(v) for v in embedding]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("non_finite_embedding")
        norm = math.sqrt(sum(v * v for v in values))
        if norm <= 1e-12:
            raise ValueError("zero_embedding")
        return [v / norm for v in values]

    def record_confidence(self, record: Dict[str, Any]) -> Dict[str, Any]:
        signals = {
            "identity": bool(
                record.get("external_id")
                and record.get("title")
                and record.get("artist_name")
            ),
            "release": record.get("release_year") is not None,
            "tempo": record.get("bpm") is not None,
            "key": bool(record.get("musical_key")),
            "genre": bool(record.get("genres")),
            "instrumentation": bool(record.get("instruments")),
            "provenance": bool(
                ((record.get("metadata") or {}).get("provenance") or {}).get(
                    "source_name"
                )
            ),
            "rights": bool((record.get("rights") or {}).get("status")),
        }
        weights = {
            "identity": 0.24,
            "release": 0.08,
            "tempo": 0.10,
            "key": 0.08,
            "genre": 0.10,
            "instrumentation": 0.08,
            "provenance": 0.16,
            "rights": 0.16,
        }
        score = sum(weights[name] for name, present in signals.items() if present)
        return {
            "score": round(score, 4),
            "signals": signals,
            "version": self.VERSION,
        }

    def rerank(
        self,
        rows: Iterable[Dict[str, Any]],
        *,
        sample_eligible_only: bool,
        limit: int,
    ) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []
        for row in rows:
            similarity = self._bounded(row.get("similarity"), 0.0, 1.0)
            profile = row.get("production_profile") or {}
            profile_signal = sum(
                1
                for key in (
                    "era",
                    "tempo_bucket",
                    "energy",
                    "harmonic_complexity",
                    "bass_prominence",
                    "sample_chop_intensity",
                )
                if profile.get(key) is not None
            ) / 6.0
            metadata_signal = sum(
                1
                for key in ("bpm", "key", "genres", "mood", "instruments")
                if row.get(key)
            ) / 5.0

            rights_signal = 0.0
            if bool(row.get("sampling_allowed")):
                rights_signal += 0.5
            if bool(row.get("commercial_use")) or row.get("rights_status") == "user_owned":
                rights_signal += 0.5

            if sample_eligible_only and rights_signal < 1.0:
                continue

            score = (
                similarity * 0.72
                + profile_signal * 0.13
                + metadata_signal * 0.10
                + rights_signal * 0.05
            )
            enriched = dict(row)
            enriched["retrieval_score"] = round(score, 6)
            enriched["retrieval_signals"] = {
                "similarity": round(similarity, 6),
                "profile_completeness": round(profile_signal, 4),
                "metadata_completeness": round(metadata_signal, 4),
                "rights_confidence": round(rights_signal, 4),
                "version": self.VERSION,
            }
            ranked.append(enriched)

        ranked.sort(
            key=lambda row: (
                -float(row.get("retrieval_score") or 0.0),
                str(row.get("external_id") or row.get("id") or ""),
            )
        )
        return ranked[: max(1, min(int(limit), self.MAX_GUIDANCE_ROWS))]

    def context_fingerprint(self, rows: Iterable[Dict[str, Any]]) -> str:
        stable = "|".join(
            str(row.get("external_id") or row.get("id") or "")
            for row in rows
        )
        return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]

    def _bounded(self, value: Any, minimum: float, maximum: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return minimum
        if not math.isfinite(parsed):
            return minimum
        return max(minimum, min(maximum, parsed))
