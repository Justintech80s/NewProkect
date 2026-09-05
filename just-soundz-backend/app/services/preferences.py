from __future__ import annotations

import json
import os
from typing import Any, Dict


class PreferenceLearningStore:
    """Learns broad production preferences from explicit user feedback."""

    TRAITS = (
        "swing",
        "syncopation",
        "negative_space",
        "kick_density",
        "snare_density",
        "percussion_complexity",
        "bass_prominence",
        "harmonic_complexity",
        "sample_chop_intensity",
        "arrangement_density",
        "lofi_character",
        "mix_polish",
        "brightness",
        "transient_punch",
        "dynamic_range",
    )

    def __init__(self):
        self.database_url = os.getenv("JUST_MAKER_DATABASE_URL")

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        if not self.configured:
            return {
                "configured": False,
                "traits": {},
                "feedback_count": 0,
            }

        import psycopg
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT traits,feedback_count,updated_at
                    FROM user_music_preferences
                    WHERE user_id=%s::uuid
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

        if not row:
            return {
                "configured": True,
                "traits": {},
                "feedback_count": 0,
                "updated_at": None,
            }

        return {
            "configured": True,
            "traits": row[0] or {},
            "feedback_count": int(row[1] or 0),
            "updated_at": row[2].isoformat() if row[2] else None,
        }

    def apply_to_plan(
        self,
        user_id: str | None,
        plan: Dict[str, Any],
        max_weight: float = 0.22,
    ) -> Dict[str, Any]:
        if not user_id:
            return plan

        profile = self.get_profile(user_id)
        traits = profile.get("traits") or {}
        count = int(profile.get("feedback_count") or 0)
        if not traits or count <= 0:
            return plan

        confidence = min(1.0, count / 12.0)
        weight = max(0.0, min(max_weight, max_weight * confidence))

        enriched = dict(plan)
        dna = dict(enriched.get("producer_dna") or {})
        applied = {}

        for trait in self.TRAITS:
            if trait not in traits or dna.get(trait) is None:
                continue
            base = float(dna[trait])
            pref = float(traits[trait])
            value = base * (1.0 - weight) + pref * weight
            dna[trait] = round(max(0.0, min(1.0, value)), 4)
            applied[trait] = dna[trait]

        dna["personalization_applied"] = bool(applied)
        dna["personalization_weight"] = round(weight, 4)
        dna["personalization_feedback_count"] = count
        enriched["producer_dna"] = dna
        enriched["preference_profile"] = {
            "feedback_count": count,
            "weight": round(weight, 4),
            "applied_traits": applied,
        }
        return enriched

    def save_feedback(
        self,
        *,
        user_id: str,
        job_id: str,
        rating: int,
        action: str,
        notes: str | None = None,
    ) -> Dict[str, Any]:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError("rating must be between 1 and 5")

        action = str(action).strip().lower()
        if action not in {"like", "dislike", "save", "reject"}:
            raise ValueError("unsupported feedback action")

        if not self.configured:
            return {
                "stored": False,
                "reason": "preference_database_not_configured",
            }

        import psycopg

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT result_payload
                    FROM generation_jobs
                    WHERE id=%s::uuid AND user_id=%s::uuid
                    """,
                    (job_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    raise PermissionError("job not found for user")

                result_payload = row[0] or {}
                dna = ((result_payload.get("plan") or {}).get("producer_dna") or {})
                learned = {
                    trait: float(dna[trait])
                    for trait in self.TRAITS
                    if dna.get(trait) is not None
                }

                cur.execute(
                    """
                    INSERT INTO generation_feedback(
                        user_id,job_id,rating,action,notes,learned_traits
                    )
                    VALUES (%s::uuid,%s::uuid,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (user_id,job_id)
                    DO UPDATE SET
                        rating=EXCLUDED.rating,
                        action=EXCLUDED.action,
                        notes=EXCLUDED.notes,
                        learned_traits=EXCLUDED.learned_traits,
                        updated_at=NOW()
                    """,
                    (
                        user_id,
                        job_id,
                        rating,
                        action,
                        notes,
                        json.dumps(learned),
                    ),
                )
                conn.commit()

        profile = self.rebuild_profile(user_id)
        return {
            "stored": True,
            "job_id": job_id,
            "rating": rating,
            "action": action,
            "profile": profile,
        }

    def rebuild_profile(self, user_id: str) -> Dict[str, Any]:
        if not self.configured:
            return {"traits": {}, "feedback_count": 0}

        import psycopg

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rating,action,learned_traits
                    FROM generation_feedback
                    WHERE user_id=%s::uuid
                    ORDER BY updated_at
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()

                weighted_sum: Dict[str, float] = {}
                weights: Dict[str, float] = {}

                for rating, action, traits in rows:
                    traits = traits or {}
                    positive = action in {"like", "save"}
                    polarity = 1.0 if positive else -1.0
                    magnitude = max(0.2, abs(float(rating) - 3.0) / 2.0)

                    for trait, raw in traits.items():
                        if trait not in self.TRAITS:
                            continue
                        value = float(raw)
                        # Negative feedback learns the opposite direction, but softly.
                        target = value if polarity > 0 else 1.0 - value
                        weight = magnitude if polarity > 0 else magnitude * 0.55
                        weighted_sum[trait] = weighted_sum.get(trait, 0.0) + target * weight
                        weights[trait] = weights.get(trait, 0.0) + weight

                profile = {
                    trait: round(weighted_sum[trait] / weights[trait], 4)
                    for trait in weighted_sum
                    if weights.get(trait, 0.0) > 0
                }

                cur.execute(
                    """
                    INSERT INTO user_music_preferences(user_id,traits,feedback_count)
                    VALUES (%s::uuid,%s::jsonb,%s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        traits=EXCLUDED.traits,
                        feedback_count=EXCLUDED.feedback_count,
                        updated_at=NOW()
                    """,
                    (user_id, json.dumps(profile), len(rows)),
                )
                conn.commit()

        return {
            "traits": profile,
            "feedback_count": len(rows),
        }
