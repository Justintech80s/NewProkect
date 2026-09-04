from __future__ import annotations

from typing import Any, Dict


AUTOMATICALLY_ELIGIBLE = {
    "public_domain",
    "royalty_free",
    "licensed",
    "partner_cleared",
    "user_owned",
    "creative_commons_sampling_allowed",
}


class SampleRightsEngine:
    """Determines whether audio may be automatically sampled by Just Maker."""

    def evaluate(self, rights: Dict[str, Any]) -> Dict[str, Any]:
        status = str(rights.get("status", "unknown")).strip().lower()
        commercial_use = bool(rights.get("commercial_use", False))
        sampling_allowed = bool(rights.get("sampling_allowed", False))

        eligible = (
            status in AUTOMATICALLY_ELIGIBLE
            and sampling_allowed
            and (commercial_use or status == "user_owned")
        )

        return {
            "status": status,
            "eligible_for_automatic_sampling": eligible,
            "reference_only": not eligible,
            "reason": self._reason(status, eligible),
        }

    def _reason(self, status: str, eligible: bool) -> str:
        if eligible:
            return "rights permit automatic sampling"
        if status in {"copyrighted", "unknown", "reference_only"}:
            return "metadata/reference use only until rights are confirmed"
        return "sampling permission is incomplete"
