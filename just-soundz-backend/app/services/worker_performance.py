from __future__ import annotations

import os
from typing import Any, Dict


class WorkerPerformanceStore:
    """Reads historical generation evaluation data for routing decisions."""

    def __init__(self):
        self.database_url = os.getenv("JUST_MAKER_DATABASE_URL")
        self.min_samples = int(os.getenv("JUST_MAKER_ROUTING_MIN_EVALUATIONS", "5"))

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    def summary(self) -> Dict[str, Dict[str, Any]]:
        if not self.configured:
            return {}

        import psycopg

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        routing->>'selected_worker' AS worker,
                        count(*)::int AS evaluations,
                        avg(overall_score)::float AS average_score,
                        avg(CASE WHEN passed THEN 1.0 ELSE 0.0 END)::float AS pass_rate
                    FROM generation_evaluations
                    WHERE routing->>'selected_worker' IS NOT NULL
                    GROUP BY routing->>'selected_worker'
                    """
                )
                rows = cur.fetchall()

        return {
            str(r[0]): {
                "evaluations": int(r[1]),
                "average_score": round(float(r[2] or 0.0), 4),
                "pass_rate": round(float(r[3] or 0.0), 4),
                "eligible": int(r[1]) >= self.min_samples,
            }
            for r in rows
        }

    def routing_bonus(
        self,
        worker_name: str,
        summaries: Dict[str, Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        stats = (summaries if summaries is not None else self.summary()).get(worker_name)
        if not stats or not stats.get("eligible"):
            return {
                "bonus": 0.0,
                "history": stats or {},
                "reason": "insufficient_history",
            }

        average = float(stats.get("average_score") or 0.0)
        pass_rate = float(stats.get("pass_rate") or 0.0)

        # Historical performance can influence routing, but capability coverage
        # remains dominant. Bonus is intentionally capped at 0.12.
        normalized_quality = max(0.0, min(1.0, average))
        normalized_pass = max(0.0, min(1.0, pass_rate))
        bonus = min(0.12, 0.08 * normalized_quality + 0.04 * normalized_pass)

        return {
            "bonus": round(bonus, 4),
            "history": stats,
            "reason": "historical_quality",
        }
