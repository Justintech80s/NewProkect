from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class ProvenanceRecord:
    source_name: str
    source_record_id: str
    source_url: Optional[str] = None
    retrieved_at: str = ""
    license_name: Optional[str] = None
    metadata_only: bool = True

    def __post_init__(self):
        if not self.retrieved_at:
            self.retrieved_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
