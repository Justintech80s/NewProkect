from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


class DatasetQualityGate:
    """Cheap deterministic validation/deduplication before expensive enrichment."""

    def validate(self, record: Dict[str, Any]) -> Dict[str, Any]:
        errors = []
        for field in ("external_id", "title", "artist_name"):
            if not str(record.get(field) or "").strip():
                errors.append(f"missing_{field}")

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
                if bpm_value <= 0 or bpm_value > 400:
                    errors.append("invalid_bpm")
            except (TypeError, ValueError):
                errors.append("invalid_bpm")

        rights = record.get("rights") or {}
        if not isinstance(rights, dict):
            errors.append("invalid_rights")

        return {"valid": not errors, "errors": errors}

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
