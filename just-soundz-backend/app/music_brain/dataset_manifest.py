from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class DatasetManifest:
    source_name: str
    metadata_only: bool = True
    sampling_allowed_by_default: bool = False
    commercial_use_by_default: bool = False
    license_name: str = "source terms apply"
    batch_size: int = 500
    checkpoint_every: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def apply(self, record: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(record)
        metadata = dict(out.get("metadata") or {})
        provenance = dict(metadata.get("provenance") or {})
        provenance.setdefault("source_name", self.source_name)
        provenance.setdefault("license_name", self.license_name)
        provenance.setdefault("metadata_only", self.metadata_only)
        metadata["provenance"] = provenance
        out["metadata"] = metadata

        # Metadata datasets never become sampleable merely because they were ingested.
        rights = dict(out.get("rights") or {})
        rights.setdefault("status", "reference_only")
        rights.setdefault("source", self.source_name)
        rights.setdefault("sampling_allowed", self.sampling_allowed_by_default)
        rights.setdefault("commercial_use", self.commercial_use_by_default)
        out["rights"] = rights
        return out
