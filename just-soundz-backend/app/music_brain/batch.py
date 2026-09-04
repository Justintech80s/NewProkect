from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from .checkpoints import CheckpointStore
from .database import MusicDatabase
from .ingestion import MusicIngestionPipeline
from .sources.musicbrainz import MusicBrainzSource


class DatasetBatchIngestor:
    """Resumable metadata batch importer for the Just Maker Music Brain."""

    def __init__(self):
        self.pipeline = MusicIngestionPipeline()
        self.database = MusicDatabase()
        self.checkpoints = CheckpointStore()
        self.musicbrainz = MusicBrainzSource()

    def ingest_records(
        self,
        records: Iterable[Dict[str, Any]],
        job_id: Optional[str] = None,
        source_name: str = "manual",
        checkpoint_every: int = 50,
    ) -> Dict[str, Any]:
        job_id = job_id or str(uuid.uuid4())
        started = datetime.now(timezone.utc).isoformat()
        processed = 0
        stored = 0
        failed = 0
        errors = []

        for record in records:
            processed += 1
            try:
                result = self.pipeline.ingest(record)
                if result.get("database", {}).get("stored"):
                    stored += 1
            except Exception as exc:
                failed += 1
                if len(errors) < 25:
                    errors.append({
                        "index": processed,
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    })

            if processed % max(checkpoint_every, 1) == 0:
                checkpoint = {
                    "job_id": job_id,
                    "source": source_name,
                    "processed": processed,
                    "stored": stored,
                    "failed": failed,
                    "status": "running",
                    "started_at": started,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                self.checkpoints.save(job_id, checkpoint)
                self.database.save_ingestion_job(checkpoint)

        final = {
            "job_id": job_id,
            "source": source_name,
            "processed": processed,
            "stored": stored,
            "failed": failed,
            "errors": errors,
            "status": "complete",
            "started_at": started,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.checkpoints.save(job_id, final)
        self.database.save_ingestion_job(final)
        return final

    def ingest_musicbrainz_query(
        self,
        query: str,
        max_records: int = 1000,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        records = self.musicbrainz.iter_recordings(
            query=query,
            max_records=max_records,
        )
        result = self.ingest_records(
            records,
            job_id=job_id,
            source_name="musicbrainz",
        )
        result["query"] = query
        self.database.save_ingestion_job(result)
        self.checkpoints.save(result["job_id"], result)
        return result
