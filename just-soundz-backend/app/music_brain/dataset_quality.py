from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict

from .intelligence import DatasetIntelligence


ALLOWED_RIGHTS_STATUSES = {
    "unknown",
    "reference_only",
    "copyrighted",
    "public_domain",
    "royalty_free",
    "licensed",
    "partner_cleared",
    "user_owned",
    "creative_commons_sampling_allowed",
}


class DatasetQualityGate:
    """Deterministic validation/deduplication before expensive enrichment."""

    def __init__(self):
        self.intelligence = DatasetIntelligence()

    def validate(self, record: Dict[str, Any]) -> Dict[str, Any]:
        errors = []
        warnings = []
        for field in ("external_id", "title", "artist_name"):
            value = str(record.get(field) or "").strip()
            if not value:
                errors.append(f"missing_{field}")
            elif len(value) > 500:
                errors.append(f"{field}_too_long")

        year = record.get("release_year")
        if year is not None:
            try:
                year_value = int(year)
                if year_value < 1800 or year_value > 2200:
                    errors.append("invalid_release_year")
            except (TypeError, ValueError):
                errors.append("invalid_release_year")

        bpm = record.get("bpm")
        if bpm is not None:
            try:
                bpm_value = float(bpm)
                if not math.isfinite(bpm_value) or bpm_value < 20 or bpm_value > 400:
                    errors.append("invalid_bpm")
            except (TypeError, ValueError):
                errors.append("invalid_bpm")

        for field in (
            "genres",
            "mood",
            "instruments",
            "producers",
            "writers",
            "performers",
            "techniques",
            "texture_tags",
        ):
            value = record.get(field)
            if value is not None and not isinstance(value, (list, tuple, set)):
                errors.append(f"invalid_{field}")

        metadata = record.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            errors.append("invalid_metadata")

        rights = record.get("rights") or {}
        if not isinstance(rights, dict):
            errors.append("invalid_rights")
            rights = {}
        status = str(rights.get("status") or "unknown").strip().lower()
        if status not in ALLOWED_RIGHTS_STATUSES:
            errors.append("invalid_rights_status")

        sampling_allowed = bool(rights.get("sampling_allowed", False))
        commercial_use = bool(rights.get("commercial_use", False))
        if sampling_allowed and status in {"unknown", "reference_only", "copyrighted"}:
            errors.append("sampling_not_supported_by_rights_status")
        if commercial_use and status in {"unknown", "reference_only", "copyrighted"}:
            errors.append("commercial_use_not_supported_by_rights_status")

        provenance = (
            (metadata or {}).get("provenance")
            if isinstance(metadata, dict)
            else None
        )
        if not provenance:
            warnings.append("missing_provenance")

        confidence = self.intelligence.record_confidence(record)
        return {
            "valid": not errors,
            "errors": sorted(set(errors)),
            "warnings": sorted(set(warnings)),
            "confidence": confidence,
        }

    def fingerprint(self, record: Dict[str, Any]) -> str:
        canonical = {
            "external_id": str(record.get("external_id") or "").strip().lower(),
            "title": str(record.get("title") or "").strip().lower(),
            "artist_name": str(record.get("artist_name") or "").strip().lower(),
            "album_name": str(record.get("album_name") or "").strip().lower(),
            "release_year": record.get("release_year"),
        }
        raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
