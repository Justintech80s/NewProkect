from __future__ import annotations

import hashlib
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List


class ArtifactManifest:
    """Builds durable metadata for generated audio/stem artifacts."""

    def from_path(
        self,
        path: str,
        artifact_type: str,
        job_id: str,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(path)

        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        return {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "artifact_type": artifact_type,
            "filename": p.name,
            "local_path": str(p),
            "content_type": mimetypes.guess_type(p.name)[0] or "application/octet-stream",
            "size_bytes": p.stat().st_size,
            "sha256": digest,
            "metadata": metadata or {},
        }


class ArtifactStore:
    """Supabase Storage adapter with a safe local-manifest fallback."""

    def __init__(self):
        self.supabase_url = os.getenv("JUST_MAKER_SUPABASE_URL")
        self.service_role_key = os.getenv("JUST_MAKER_SUPABASE_SERVICE_ROLE_KEY")
        self.bucket = os.getenv("JUST_MAKER_ARTIFACT_BUCKET", "just-maker-artifacts")

    @property
    def configured(self) -> bool:
        return bool(self.supabase_url and self.service_role_key)

    def persist(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured:
            return {
                **artifact,
                "persisted": False,
                "reason": "artifact_storage_not_configured",
            }

        import httpx

        path = Path(artifact["local_path"])
        object_path = f"{artifact['job_id']}/{artifact['id']}/{artifact['filename']}"
        url = (
            f"{self.supabase_url.rstrip('/')}/storage/v1/object/"
            f"{self.bucket}/{object_path}"
        )
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
            "Content-Type": artifact["content_type"],
            "x-upsert": "true",
        }

        with path.open("rb") as f:
            response = httpx.post(
                url,
                content=f.read(),
                headers=headers,
                timeout=120,
            )
        response.raise_for_status()

        return {
            **artifact,
            "persisted": True,
            "bucket": self.bucket,
            "object_path": object_path,
            "storage_uri": f"supabase://{self.bucket}/{object_path}",
        }

    def persist_many(self, artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.persist(item) for item in artifacts]
