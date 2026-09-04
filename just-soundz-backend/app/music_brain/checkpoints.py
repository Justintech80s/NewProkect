from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class CheckpointStore:
    """Local fallback checkpoint store for batch ingestion.

    Production can persist the same state in Postgres. This keeps long imports
    resumable during development and worker execution.
    """

    def __init__(self, base_dir: str = "/tmp/just-maker-checkpoints"):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def load(self, job_id: str) -> Optional[Dict[str, Any]]:
        path = self.base / f"{job_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save(self, job_id: str, payload: Dict[str, Any]) -> None:
        path = self.base / f"{job_id}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def delete(self, job_id: str) -> None:
        path = self.base / f"{job_id}.json"
        if path.exists():
            path.unlink()
