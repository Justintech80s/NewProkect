from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from .checkpoints import CheckpointStore
from .database import MusicDatabase
from .dataset_manifest import DatasetManifest
from .dataset_quality import DatasetQualityGate
from .ingestion import MusicIngestionPipeline
from .sources.musicbrainz import MusicBrainzSource


class DatasetBatchIngestor:
    """Resumable metadata batch importer for the Just Maker Music Brain."""

    def __init__(self):
        self.pipeline = MusicIngestionPipeline()
        self.database = MusicDatabase()
        self.checkpoints = CheckpointStore()
        self.musicbrainz = MusicBrainzSource()
        self.quality = DatasetQualityGate()

    def ingest_records(
        self,
        records: Iterable[Dict[str, Any]],
        job_id: Optional[str] = None,
        source_name: str = "manual",
        checkpoint_every: int = 50,
        manifest: Optional[DatasetManifest] = None,
        deduplicate: bool = True,
        max_error_samples: int = 25,
    ) -> Dict[str, Any]:
        job_id = job_id or str(uuid.uuid4())
        started = datetime.now(timezone.utc).isoformat()
        processed = 0
        stored = 0
        failed = 0
        rejected = 0
        duplicates = 0
        errors = []
        seen = set()

        for record in records:
            processed += 1
            try:
                candidate = manifest.apply(record) if manifest else dict(record)
                quality = self.quality.validate(candidate)
                if not quality["valid"]:
                    rejected += 1
                    if len(errors) < max_error_samples:
                        errors.append({
                            "index": processed,
                            "type": "DatasetQualityError",
                            "message": ",".join(quality["errors"]),
                        })
                    continue

                fingerprint = self.quality.fingerprint(candidate)
                if deduplicate and fingerprint in seen:
                    duplicates += 1
                    continue
                seen.add(fingerprint)

                result = self.pipeline.ingest(candidate)
                if result.get("database", {}).get("stored"):
                    stored += 1
            except Exception as exc:
                failed += 1
                if len(errors) < max_error_samples:
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
                    "rejected": rejected,
                    "duplicates": duplicates,
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
            "rejected": rejected,
            "duplicates": duplicates,
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
            manifest=DatasetManifest(
                source_name="musicbrainz",
                metadata_only=True,
                sampling_allowed_by_default=False,
                commercial_use_by_default=False,
                license_name="MusicBrainz metadata terms apply",
            ),
        )
        result["query"] = query
        self.database.save_ingestion_job(result)
        self.checkpoints.save(result["job_id"], result)
        return result
