from __future__ import annotations

import json
import os
from typing import Any, Dict, List


class EvaluationStore:
    def __init__(self):
        self.database_url = os.getenv("JUST_MAKER_DATABASE_URL")

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    def save(
        self,
        job_id: str,
        user_id: str | None,
        evaluation: Dict[str, Any],
    ) -> None:
        if not self.configured:
            return

        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO generation_evaluations(
                        job_id,user_id,provider,overall_score,grade,passed,
                        scores,issues,routing
                    )
                    VALUES (%s::uuid,%s::uuid,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)
                    ON CONFLICT (job_id)
                    DO UPDATE SET
                        provider=EXCLUDED.provider,
                        overall_score=EXCLUDED.overall_score,
                        grade=EXCLUDED.grade,
                        passed=EXCLUDED.passed,
                        scores=EXCLUDED.scores,
                        issues=EXCLUDED.issues,
                        routing=EXCLUDED.routing,
                        updated_at=NOW()
                    """,
                    (
                        job_id,
                        user_id,
                        evaluation.get("provider"),
                        float(evaluation.get("score") or 0.0),
                        evaluation.get("grade"),
                        bool(evaluation.get("pass")),
                        json.dumps(evaluation.get("scores") or {}),
                        json.dumps(evaluation.get("issues") or []),
                        json.dumps(evaluation.get("routing") or {}),
                    ),
                )
                conn.commit()

    def provider_summary(self) -> List[Dict[str, Any]]:
        if not self.configured:
            return []

        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT provider,
                           count(*)::int,
                           avg(overall_score)::float,
                           avg(CASE WHEN passed THEN 1.0 ELSE 0.0 END)::float,
                           max(updated_at)
                    FROM generation_evaluations
                    WHERE provider IS NOT NULL
                    GROUP BY provider
                    ORDER BY avg(overall_score) DESC
                    """
                )
                rows = cur.fetchall()

        return [{
            "provider": r[0],
            "evaluations": r[1],
            "average_score": round(float(r[2]), 4),
            "pass_rate": round(float(r[3]), 4),
            "last_evaluated_at": r[4].isoformat() if r[4] else None,
        } for r in rows]
