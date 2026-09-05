from __future__ import annotations

import json
import os
from typing import Any, Dict, List


class CreativeMemoryStore:
    """Stores compact production recipes from successful generations.

    Audio is not duplicated here. Memory contains broad controls and planning
    metadata so future generations can reuse what worked without cloning a song.
    """

    def __init__(self):
        self.database_url = os.getenv("JUST_MAKER_DATABASE_URL")

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    def remember(self, user_id: str | None, job_id: str, result: Dict[str, Any]) -> None:
        if not self.configured or not user_id:
            return
        evaluation = result.get("evaluation") or {}
        if not bool(evaluation.get("pass")):
            return

        plan = result.get("plan") or {}
        recipe = {
            "producer_dna": self._clean_dna(plan.get("producer_dna") or {}),
            "harmony_plan": plan.get("harmony_plan") or {},
            "instrumentation_plan": plan.get("instrumentation_plan") or {},
            "arrangement": plan.get("arrangement") or [],
            "bpm": plan.get("bpm"),
            "key": plan.get("key"),
            "mood": plan.get("mood") or [],
            "genres": (plan.get("production_context") or {}).get("genres") or [],
        }

        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO creative_memories(
                        user_id,job_id,score,recipe
                    )
                    VALUES (%s::uuid,%s::uuid,%s,%s::jsonb)
                    ON CONFLICT (user_id,job_id)
                    DO UPDATE SET
                        score=EXCLUDED.score,
                        recipe=EXCLUDED.recipe,
                        updated_at=NOW()
                    """,
                    (
                        user_id,
                        job_id,
                        float(evaluation.get("score") or 0.0),
                        json.dumps(recipe),
                    ),
                )
                conn.commit()

    def best(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.configured:
            return []
        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT job_id::text,score,recipe,updated_at
                    FROM creative_memories
                    WHERE user_id=%s::uuid
                    ORDER BY score DESC,updated_at DESC
                    LIMIT %s
                    """,
                    (user_id, max(1, min(int(limit), 20))),
                )
                rows = cur.fetchall()
        return [{
            "job_id": r[0],
            "score": round(float(r[1]), 4),
            "recipe": r[2] or {},
            "updated_at": r[3].isoformat() if r[3] else None,
        } for r in rows]

    def apply(self, user_id: str | None, plan: Dict[str, Any]) -> Dict[str, Any]:
        if not user_id:
            return plan
        memories = self.best(user_id, limit=3)
        if not memories:
            return plan

        enriched = dict(plan)
        dna = dict(enriched.get("producer_dna") or {})
        weighted = {}
        totals = {}
        for memory in memories:
            score = max(0.01, float(memory.get("score") or 0.0))
            mdna = (memory.get("recipe") or {}).get("producer_dna") or {}
            for key, raw in mdna.items():
                if isinstance(raw, (int, float)):
                    weighted[key] = weighted.get(key, 0.0) + float(raw) * score
                    totals[key] = totals.get(key, 0.0) + score

        applied = {}
        # Keep memory influence deliberately modest; current prompt remains primary.
        weight = min(0.16, 0.05 + len(memories) * 0.035)
        for key, total in weighted.items():
            if key not in dna or not isinstance(dna.get(key), (int, float)):
                continue
            historical = total / totals[key]
            current = float(dna[key])
            value = current * (1.0 - weight) + historical * weight
            dna[key] = round(max(0.0, min(1.0, value)), 4)
            applied[key] = dna[key]

        dna["creative_memory_applied"] = bool(applied)
        dna["creative_memory_weight"] = round(weight, 4)
        enriched["producer_dna"] = dna
        enriched["creative_memory"] = {
            "source_jobs": [m["job_id"] for m in memories],
            "applied_traits": applied,
            "policy": "broad-successful-production-recipes-only",
        }
        return enriched

    def _clean_dna(self, dna: Dict[str, Any]) -> Dict[str, Any]:
        blocked = {
            "melody_sequence",
            "note_sequence",
            "exact_chords",
            "exact_arrangement",
        }
        return {
            k: v for k, v in dna.items()
            if k not in blocked and isinstance(v, (str, int, float, bool))
        }
