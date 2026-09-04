from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any, Dict, List, Optional

from .search import MusicBrainSearch


class MusicBrainContextBuilder:
    """Retrieves music knowledge and converts it into compact generation guidance."""

    def __init__(self, search: Optional[MusicBrainSearch] = None):
        self.search = search or MusicBrainSearch()

    def build(self, prompt: str, limit: int = 12) -> Dict[str, Any]:
        references = self.search.search(
            query=prompt,
            limit=limit,
            sample_eligible_only=False,
        )
        eligible = self.search.search(
            query=prompt,
            limit=max(5, limit // 2),
            sample_eligible_only=True,
        )

        ref_rows = references.get("results") or []
        eligible_rows = eligible.get("results") or []

        bpms = [float(r["bpm"]) for r in ref_rows if r.get("bpm") is not None]
        keys = [str(r["key"]) for r in ref_rows if r.get("key")]
        genres: List[str] = []
        moods: List[str] = []
        instruments: List[str] = []
        years: List[int] = []

        for row in ref_rows:
            genres.extend(str(x) for x in (row.get("genres") or []))
            moods.extend(str(x) for x in (row.get("mood") or []))
            instruments.extend(str(x) for x in (row.get("instruments") or []))
            if row.get("year"):
                years.append(int(row["year"]))

        guidance = {
            "suggested_bpm": round(median(bpms), 2) if bpms else None,
            "common_key": self._mode(keys),
            "top_genres": self._top(genres, 6),
            "top_moods": self._top(moods, 6),
            "top_instruments": self._top(instruments, 8),
            "year_range": [min(years), max(years)] if years else None,
        }

        return {
            "query": prompt,
            "database_configured": references.get("database_configured", False),
            "graph_configured": references.get("graph_configured", False),
            "reference_count": len(ref_rows),
            "eligible_sample_count": len(eligible_rows),
            "guidance": guidance,
            "references": [self._compact(r) for r in ref_rows[:limit]],
            "eligible_samples": [self._compact(r) for r in eligible_rows[:limit]],
        }

    def apply_to_plan(
        self,
        plan: Dict[str, Any],
        context: Dict[str, Any],
        user_bpm_supplied: bool,
        user_key_supplied: bool,
    ) -> Dict[str, Any]:
        enriched = dict(plan)
        guidance = context.get("guidance") or {}

        if not user_bpm_supplied and guidance.get("suggested_bpm"):
            enriched["bpm"] = int(round(float(guidance["suggested_bpm"])))

        if not user_key_supplied and guidance.get("common_key"):
            enriched["key"] = guidance["common_key"]

        enriched["music_brain"] = {
            "reference_count": context.get("reference_count", 0),
            "eligible_sample_count": context.get("eligible_sample_count", 0),
            "guidance": guidance,
            "references": context.get("references", []),
            "eligible_samples": context.get("eligible_samples", []),
        }

        enriched["production_context"] = {
            "genres": guidance.get("top_genres", []),
            "moods": guidance.get("top_moods", []),
            "instruments": guidance.get("top_instruments", []),
            "era": guidance.get("year_range"),
        }
        return enriched

    def _mode(self, values: List[str]) -> Optional[str]:
        if not values:
            return None
        return Counter(values).most_common(1)[0][0]

    def _top(self, values: List[str], limit: int) -> List[str]:
        return [name for name, _ in Counter(v for v in values if v).most_common(limit)]

    def _compact(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row.get("id"),
            "title": row.get("title"),
            "artist": row.get("artist"),
            "year": row.get("year"),
            "bpm": row.get("bpm"),
            "key": row.get("key"),
            "genres": row.get("genres") or [],
            "mood": row.get("mood") or [],
            "instruments": row.get("instruments") or [],
            "rights_status": row.get("rights_status"),
            "sampling_allowed": bool(row.get("sampling_allowed", False)),
            "commercial_use": bool(row.get("commercial_use", False)),
            "source_uri": row.get("source_uri"),
            "storage_uri": row.get("storage_uri"),
            "similarity": row.get("similarity"),
        }
