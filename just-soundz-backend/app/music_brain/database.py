from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional


class MusicDatabase:
    """PostgreSQL/pgvector adapter for the Just Maker Music Brain."""

    def __init__(self):
        self.url = os.getenv("JUST_MAKER_DATABASE_URL")

    @property
    def configured(self) -> bool:
        return bool(self.url)

    @contextmanager
    def connection(self):
        if not self.url:
            raise RuntimeError("JUST_MAKER_DATABASE_URL is not configured")
        import psycopg
        with psycopg.connect(self.url) as conn:
            yield conn

    def upsert_song(self, song: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured:
            return {"stored": False, "reason": "database_not_configured", "song": song}

        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO songs (
                        external_id, title, artist_name, album_name, release_year,
                        bpm, musical_key, genres, mood, instruments, metadata
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (external_id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        artist_name = EXCLUDED.artist_name,
                        album_name = EXCLUDED.album_name,
                        release_year = EXCLUDED.release_year,
                        bpm = EXCLUDED.bpm,
                        musical_key = EXCLUDED.musical_key,
                        genres = EXCLUDED.genres,
                        mood = EXCLUDED.mood,
                        instruments = EXCLUDED.instruments,
                        metadata = EXCLUDED.metadata
                    RETURNING id
                    """,
                    (
                        song["external_id"],
                        song["title"],
                        song["artist_name"],
                        song.get("album_name"),
                        song.get("release_year"),
                        song.get("bpm"),
                        song.get("musical_key"),
                        song.get("genres", []),
                        song.get("mood", []),
                        song.get("instruments", []),
                        json.dumps(song.get("metadata", {})),
                    ),
                )
                song_id = cur.fetchone()[0]
                conn.commit()
        return {"stored": True, "id": song_id}

    def set_rights(self, song_id: int, rights: Dict[str, Any]) -> None:
        if not self.configured:
            return
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO song_rights (
                        song_id, status, source, license_name,
                        commercial_use, sampling_allowed, metadata
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (song_id)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        source = EXCLUDED.source,
                        license_name = EXCLUDED.license_name,
                        commercial_use = EXCLUDED.commercial_use,
                        sampling_allowed = EXCLUDED.sampling_allowed,
                        metadata = EXCLUDED.metadata
                    """,
                    (
                        song_id,
                        rights.get("status", "unknown"),
                        rights.get("source"),
                        rights.get("license_name"),
                        bool(rights.get("commercial_use", False)),
                        bool(rights.get("sampling_allowed", False)),
                        json.dumps(rights.get("metadata", {})),
                    ),
                )
                conn.commit()

    def set_embedding(self, song_id: int, embedding: Iterable[float]) -> None:
        if not self.configured:
            return
        vector = "[" + ",".join(str(float(x)) for x in embedding) + "]"
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO song_embeddings (song_id, embedding)
                    VALUES (%s, %s::extensions.vector)
                    ON CONFLICT (song_id)
                    DO UPDATE SET embedding = EXCLUDED.embedding
                    """,
                    (song_id, vector),
                )
                conn.commit()

    def semantic_search(
        self,
        embedding: Iterable[float],
        limit: int = 20,
        only_sample_eligible: bool = False,
    ) -> List[Dict[str, Any]]:
        if not self.configured:
            return []

        vector = "[" + ",".join(str(float(x)) for x in embedding) + "]"
        rights_clause = """
            AND r.sampling_allowed = TRUE
            AND (r.commercial_use = TRUE OR r.status = 'user_owned')
        """ if only_sample_eligible else ""

        sql = f"""
            SELECT
                s.id, s.external_id, s.title, s.artist_name, s.album_name, s.release_year,
                s.bpm, s.musical_key, s.genres, s.mood, s.instruments,
                r.status, r.sampling_allowed, r.commercial_use,
                1 - (e.embedding <=> %s::extensions.vector) AS similarity
            FROM song_embeddings e
            JOIN songs s ON s.id = e.song_id
            LEFT JOIN song_rights r ON r.song_id = s.id
            WHERE 1=1
            {rights_clause}
            ORDER BY e.embedding <=> %s::extensions.vector
            LIMIT %s
        """

        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (vector, vector, limit))
                rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "external_id": row[1],
                "title": row[2],
                "artist": row[3],
                "album": row[4],
                "year": row[5],
                "bpm": row[6],
                "key": row[7],
                "genres": row[8] or [],
                "mood": row[9] or [],
                "instruments": row[10] or [],
                "rights_status": row[11],
                "sampling_allowed": row[12],
                "commercial_use": row[13],
                "similarity": float(row[14]),
            }
            for row in rows
        ]


    def set_provenance(self, song_id: int, provenance: Dict[str, Any]) -> None:
        if not self.configured or not provenance:
            return
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO record_provenance (
                        song_id, source_name, source_record_id, source_url,
                        retrieved_at, license_name, metadata_only, metadata
                    )
                    VALUES (%s,%s,%s,%s,COALESCE(%s::timestamptz,NOW()),%s,%s,%s::jsonb)
                    ON CONFLICT (source_name, source_record_id)
                    DO UPDATE SET
                        song_id = EXCLUDED.song_id,
                        source_url = EXCLUDED.source_url,
                        retrieved_at = EXCLUDED.retrieved_at,
                        license_name = EXCLUDED.license_name,
                        metadata_only = EXCLUDED.metadata_only,
                        metadata = EXCLUDED.metadata
                    """,
                    (
                        song_id,
                        provenance.get("source_name"),
                        provenance.get("source_record_id"),
                        provenance.get("source_url"),
                        provenance.get("retrieved_at"),
                        provenance.get("license_name"),
                        bool(provenance.get("metadata_only", True)),
                        json.dumps(provenance.get("metadata", {})),
                    ),
                )
                conn.commit()

    def save_ingestion_job(self, payload: Dict[str, Any]) -> None:
        if not self.configured:
            return
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ingestion_jobs (
                        id, source_name, query, status, processed_count,
                        stored_count, failed_count, checkpoint, error_summary,
                        started_at, completed_at, updated_at
                    )
                    VALUES (
                        %s::uuid,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,
                        %s::timestamptz,%s::timestamptz,NOW()
                    )
                    ON CONFLICT (id)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        processed_count = EXCLUDED.processed_count,
                        stored_count = EXCLUDED.stored_count,
                        failed_count = EXCLUDED.failed_count,
                        checkpoint = EXCLUDED.checkpoint,
                        error_summary = EXCLUDED.error_summary,
                        completed_at = EXCLUDED.completed_at,
                        updated_at = NOW()
                    """,
                    (
                        payload["job_id"],
                        payload.get("source", "manual"),
                        payload.get("query"),
                        payload.get("status", "running"),
                        int(payload.get("processed", 0)),
                        int(payload.get("stored", 0)),
                        int(payload.get("failed", 0)),
                        json.dumps(payload),
                        json.dumps(payload.get("errors", [])),
                        payload.get("started_at"),
                        payload.get("completed_at"),
                    ),
                )
                conn.commit()

    def get_ingestion_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if not self.configured:
            return None
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id::text, source_name, query, status, processed_count,
                           stored_count, failed_count, checkpoint, error_summary,
                           started_at, completed_at, updated_at
                    FROM ingestion_jobs
                    WHERE id = %s::uuid
                    """,
                    (job_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return {
            "job_id": row[0],
            "source": row[1],
            "query": row[2],
            "status": row[3],
            "processed": row[4],
            "stored": row[5],
            "failed": row[6],
            "checkpoint": row[7],
            "errors": row[8],
            "started_at": row[9].isoformat() if row[9] else None,
            "completed_at": row[10].isoformat() if row[10] else None,
            "updated_at": row[11].isoformat() if row[11] else None,
        }


    def semantic_sample_search(
        self,
        embedding: Iterable[float],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search only cleared sample assets linked to song embeddings."""
        if not self.configured:
            return []

        vector = "[" + ",".join(str(float(x)) for x in embedding) + "]"
        sql = """
            SELECT
                sa.id, sa.source_uri, sa.storage_uri, sa.rights_status,
                sa.sampling_allowed, sa.commercial_use, sa.duration_seconds,
                COALESCE(sa.bpm, s.bpm) AS bpm,
                COALESCE(sa.musical_key, s.musical_key) AS musical_key,
                s.id AS song_id, s.external_id, s.title, s.artist_name,
                s.release_year, s.genres, s.mood, s.instruments,
                1 - (e.embedding <=> %s::extensions.vector) AS similarity
            FROM sample_assets sa
            JOIN songs s ON s.id = sa.song_id
            JOIN song_embeddings e ON e.song_id = s.id
            WHERE sa.sampling_allowed = TRUE
              AND sa.commercial_use = TRUE
            ORDER BY e.embedding <=> %s::extensions.vector
            LIMIT %s
        """
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (vector, vector, limit))
                rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "source_uri": row[1],
                "storage_uri": row[2],
                "rights_status": row[3],
                "sampling_allowed": row[4],
                "commercial_use": row[5],
                "duration_seconds": row[6],
                "bpm": row[7],
                "key": row[8],
                "song_id": row[9],
                "external_id": row[10],
                "title": row[11],
                "artist": row[12],
                "year": row[13],
                "genres": row[14] or [],
                "mood": row[15] or [],
                "instruments": row[16] or [],
                "similarity": float(row[17]),
            }
            for row in rows
        ]


    def semantic_search_with_profiles(
        self,
        embedding: Iterable[float],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        if not self.configured:
            return []

        vector = "[" + ",".join(str(float(x)) for x in embedding) + "]"
        sql = """
            SELECT
                s.id,s.external_id,s.title,s.artist_name,s.album_name,s.release_year,
                s.bpm,s.musical_key,s.genres,s.mood,s.instruments,
                p.era,p.tempo_bucket,p.energy,p.harmonic_complexity,
                p.bass_prominence,p.sample_chop_intensity,p.texture_tags,p.techniques,
                1 - (e.embedding <=> %s::extensions.vector) AS similarity
            FROM song_embeddings e
            JOIN songs s ON s.id=e.song_id
            LEFT JOIN production_profiles p ON p.song_id=s.id
            ORDER BY e.embedding <=> %s::extensions.vector
            LIMIT %s
        """
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (vector, vector, limit))
                rows = cur.fetchall()

        return [{
            "id": r[0], "external_id": r[1], "title": r[2], "artist": r[3],
            "album": r[4], "year": r[5], "bpm": r[6], "key": r[7],
            "genres": r[8] or [], "mood": r[9] or [], "instruments": r[10] or [],
            "production_profile": {
                "era": r[11], "tempo_bucket": r[12], "energy": r[13],
                "harmonic_complexity": r[14], "bass_prominence": r[15],
                "sample_chop_intensity": r[16], "texture_tags": r[17] or [],
                "techniques": r[18] or [],
            },
            "similarity": float(r[19]),
        } for r in rows]
