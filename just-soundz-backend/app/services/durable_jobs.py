from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class DurableGenerationJobStore:
    """Postgres-backed generation job store with in-process fallback compatibility."""

    def __init__(self):
        self.url = os.getenv("JUST_MAKER_DATABASE_URL")

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def create(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        job = {
            "job_id": job_id,
            "status": "queued",
            "stage": "queued",
            "progress": 0.0,
            "request": request_payload,
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        if self.configured:
            self._upsert(job)
        return job

    def update(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        progress: Optional[float] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        current = self.get(job_id) or {"job_id": job_id, "request": {}}
        if status is not None:
            current["status"] = status
        if stage is not None:
            current["stage"] = stage
        if progress is not None:
            current["progress"] = max(0.0, min(1.0, float(progress)))
        if result is not None:
            current["result"] = result
        if error is not None:
            current["error"] = error
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        if self.configured:
            self._upsert(current)
        return current

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        if not self.configured:
            return None

        import psycopg

        with psycopg.connect(self.url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id::text,status,stage,progress,request_payload,
                           result_payload,error_message,created_at,updated_at
                    FROM generation_jobs
                    WHERE id=%s::uuid
                    """,
                    (job_id,),
                )
                row = cur.fetchone()

        if not row:
            return None

        return {
            "job_id": row[0],
            "status": row[1],
            "stage": row[2],
            "progress": float(row[3]),
            "request": row[4] or {},
            "result": row[5],
            "error": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
            "updated_at": row[8].isoformat() if row[8] else None,
        }

    def save_artifact(self, artifact: Dict[str, Any]) -> None:
        if not self.configured:
            return

        import psycopg

        with psycopg.connect(self.url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO generation_artifacts (
                        id,job_id,artifact_type,filename,content_type,size_bytes,
                        sha256,bucket,object_path,storage_uri,metadata
                    )
                    VALUES (
                        %s::uuid,%s::uuid,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        bucket=EXCLUDED.bucket,
                        object_path=EXCLUDED.object_path,
                        storage_uri=EXCLUDED.storage_uri,
                        metadata=EXCLUDED.metadata
                    """,
                    (
                        artifact["id"],
                        artifact["job_id"],
                        artifact["artifact_type"],
                        artifact["filename"],
                        artifact["content_type"],
                        artifact["size_bytes"],
                        artifact["sha256"],
                        artifact.get("bucket"),
                        artifact.get("object_path"),
                        artifact.get("storage_uri"),
                        json.dumps(artifact.get("metadata", {})),
                    ),
                )
                conn.commit()

    def artifacts(self, job_id: str) -> list[Dict[str, Any]]:
        if not self.configured:
            return []

        import psycopg

        with psycopg.connect(self.url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id::text,artifact_type,filename,content_type,size_bytes,
                           sha256,bucket,object_path,storage_uri,metadata,created_at
                    FROM generation_artifacts
                    WHERE job_id=%s::uuid
                    ORDER BY created_at
                    """,
                    (job_id,),
                )
                rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "artifact_type": r[1],
                "filename": r[2],
                "content_type": r[3],
                "size_bytes": r[4],
                "sha256": r[5],
                "bucket": r[6],
                "object_path": r[7],
                "storage_uri": r[8],
                "metadata": r[9] or {},
                "created_at": r[10].isoformat() if r[10] else None,
            }
            for r in rows
        ]

    def _upsert(self, job: Dict[str, Any]) -> None:
        import psycopg

        with psycopg.connect(self.url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO generation_jobs (
                        id,status,stage,progress,request_payload,result_payload,
                        error_message,created_at,updated_at
                    )
                    VALUES (
                        %s::uuid,%s,%s,%s,%s::jsonb,%s::jsonb,%s,
                        COALESCE(%s::timestamptz,NOW()),NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        status=EXCLUDED.status,
                        stage=EXCLUDED.stage,
                        progress=EXCLUDED.progress,
                        request_payload=EXCLUDED.request_payload,
                        result_payload=EXCLUDED.result_payload,
                        error_message=EXCLUDED.error_message,
                        updated_at=NOW()
                    """,
                    (
                        job["job_id"],
                        job.get("status", "queued"),
                        job.get("stage", "queued"),
                        float(job.get("progress", 0.0)),
                        json.dumps(job.get("request", {})),
                        json.dumps(job.get("result")),
                        job.get("error"),
                        job.get("created_at"),
                    ),
                )
                conn.commit()
