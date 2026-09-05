from __future__ import annotations

from typing import Any, Dict


class OriginalityGuard:
    """Checks whether conditioning is trait-based rather than direct-copy based."""

    BLOCKED_KEYS = {
        "melody_sequence",
        "note_sequence",
        "exact_chords",
        "exact_arrangement",
        "audio_clone",
    }

    def evaluate(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        reference = plan.get("reference_audio") or {}
        policy = reference.get("policy") or {}
        violations = []

        for key in self.BLOCKED_KEYS:
            if reference.get(key):
                violations.append(key)

        if policy.get("melody_extracted"):
            violations.append("melody_extracted")
        if policy.get("note_sequence_stored"):
            violations.append("note_sequence_stored")

        return {
            "pass": not violations,
            "violations": sorted(set(violations)),
            "policy": "production-traits-only",
        }

    def apply(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        result = self.evaluate(enriched)
        enriched["originality_guard"] = result
        if not result["pass"]:
            raise ValueError(
                "Reference conditioning contains direct-copy features: "
                + ", ".join(result["violations"])
            )
        return enriched
