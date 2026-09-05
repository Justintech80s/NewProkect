from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from .database import MusicDatabase


class RelationalMusicGraph:
    """Postgres-native relationship graph used even when Neo4j is unavailable."""

    def __init__(self, db: MusicDatabase | None = None):
        self.db = db or MusicDatabase()

    @property
    def configured(self) -> bool:
        return self.db.configured

    def upsert_song(self, song_id: int, song: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured:
            return {"stored": False, "reason": "database_not_configured"}

        created = 0
        artist_id = self._entity("artist", song["artist_name"])
        song_entity_id = self._entity(
            "song",
            song["title"],
            external_id=song.get("external_id"),
            metadata={"song_id": song_id},
        )
        created += self._link(artist_id, "PERFORMED", song_entity_id, song_id)

        album = song.get("album_name")
        if album:
            album_id = self._entity("release", album)
            created += self._link(song_entity_id, "APPEARS_ON", album_id, song_id)

        for genre in song.get("genres") or []:
            genre_id = self._entity("genre", str(genre))
            created += self._link(song_entity_id, "HAS_GENRE", genre_id, song_id)

        for instrument in song.get("instruments") or []:
            inst_id = self._entity("instrument", str(instrument))
            created += self._link(song_entity_id, "USES_INSTRUMENT", inst_id, song_id)

        credits = []
        for producer in song.get("producers") or []:
            credits.append(("producer", producer, "PRODUCED"))
        for writer in song.get("writers") or []:
            credits.append(("writer", writer, "WROTE"))
        for performer in song.get("performers") or []:
            credits.append(("performer", performer, "PERFORMED_ON"))

        for credit_type, person, relation in credits:
            person_id = self._entity(credit_type, str(person))
            created += self._link(person_id, relation, song_entity_id, song_id)
            self._credit(song_id, credit_type, str(person))

        year = song.get("release_year")
        if year:
            era = self._era(int(year))
            era_id = self._entity("era", era)
            created += self._link(song_entity_id, "BELONGS_TO_ERA", era_id, song_id)

        for technique in song.get("techniques") or []:
            tech_id = self._entity("production_technique", str(technique))
            created += self._link(song_entity_id, "USES_TECHNIQUE", tech_id, song_id)

        return {"stored": True, "relationships_written": created}

    def related_songs(self, song_id: int, limit: int = 25) -> List[Dict[str, Any]]:
        if not self.configured:
            return []

        sql = """
            WITH seed_entities AS (
                SELECT DISTINCT source_entity_id AS entity_id
                FROM music_relationships WHERE song_id=%s
                UNION
                SELECT DISTINCT target_entity_id AS entity_id
                FROM music_relationships WHERE song_id=%s
            ),
            related AS (
                SELECT mr.song_id, count(*)::int AS shared_relationships,
                       sum(mr.weight)::float AS relationship_weight
                FROM music_relationships mr
                JOIN seed_entities se
                  ON mr.source_entity_id=se.entity_id
                  OR mr.target_entity_id=se.entity_id
                WHERE mr.song_id IS NOT NULL AND mr.song_id<>%s
                GROUP BY mr.song_id
            )
            SELECT s.id,s.external_id,s.title,s.artist_name,s.release_year,
                   r.shared_relationships,r.relationship_weight
            FROM related r
            JOIN songs s ON s.id=r.song_id
            ORDER BY r.relationship_weight DESC, r.shared_relationships DESC
            LIMIT %s
        """
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (song_id, song_id, song_id, limit))
                rows = cur.fetchall()

        return [{
            "id": row[0],
            "external_id": row[1],
            "title": row[2],
            "artist": row[3],
            "year": row[4],
            "shared_relationships": row[5],
            "relationship_weight": float(row[6]),
        } for row in rows]

    def _entity(
        self,
        entity_type: str,
        name: str,
        external_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> int:
        normalized = self._normalize(name)
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO music_entities(entity_type,external_id,name,normalized_name,metadata)
                    VALUES (%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (entity_type,normalized_name)
                    DO UPDATE SET
                        external_id=COALESCE(EXCLUDED.external_id,music_entities.external_id),
                        name=EXCLUDED.name,
                        metadata=music_entities.metadata || EXCLUDED.metadata,
                        updated_at=NOW()
                    RETURNING id
                    """,
                    (
                        entity_type,
                        external_id,
                        name.strip(),
                        normalized,
                        __import__("json").dumps(metadata or {}),
                    ),
                )
                entity_id = int(cur.fetchone()[0])
                conn.commit()
                return entity_id

    def _link(
        self,
        source_id: int,
        relationship_type: str,
        target_id: int,
        song_id: int,
        weight: float = 1.0,
    ) -> int:
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO music_relationships(
                        source_entity_id,relationship_type,target_entity_id,song_id,weight
                    )
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (source_entity_id,relationship_type,target_entity_id,song_id)
                    DO UPDATE SET weight=EXCLUDED.weight
                    RETURNING id
                    """,
                    (source_id, relationship_type, target_id, song_id, weight),
                )
                cur.fetchone()
                conn.commit()
        return 1

    def _credit(self, song_id: int, credit_type: str, person_name: str):
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO song_credits(song_id,credit_type,person_name)
                    VALUES (%s,%s,%s)
                    ON CONFLICT (song_id,credit_type,person_name) DO NOTHING
                    """,
                    (song_id, credit_type, person_name),
                )
                conn.commit()

    def _normalize(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    def _era(self, year: int) -> str:
        decade = (year // 10) * 10
        return f"{decade}s"
