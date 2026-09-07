from __future__ import annotations

from typing import Any, Dict


class ReadinessChecker:
    def __init__(self, *, database, router, artifact_store, user_auth):
        self.database = database
        self.router = router
        self.artifact_store = artifact_store
        self.user_auth = user_auth

    def _dependency(
        self,
        name: str,
        *,
        configured: bool,
        required: bool,
        unavailable_reason: str,
    ) -> Dict[str, Any]:
        if configured:
            status = "ready"
            reason = "available"
        elif required:
            status = "not_ready"
            reason = unavailable_reason
        else:
            status = "degraded"
            reason = unavailable_reason
        return {
            "name": name,
            "required": required,
            "status": status,
            "reason": reason,
        }

    def check(self) -> Dict[str, Any]:
        worker_available = any(
            worker.get("configured")
            for worker in self.router.status().get("workers", [])
        )

        dependencies = [
            self._dependency(
                "database",
                configured=bool(self.database.configured),
                required=True,
                unavailable_reason="not_configured",
            ),
            self._dependency(
                "generation_worker",
                configured=bool(worker_available),
                required=True,
                unavailable_reason="no_generation_worker",
            ),
            self._dependency(
                "artifact_storage",
                configured=bool(self.artifact_store.configured),
                required=False,
                unavailable_reason="not_configured",
            ),
            self._dependency(
                "user_auth",
                configured=bool(self.user_auth.configured),
                required=False,
                unavailable_reason="not_configured",
            ),
        ]

        if any(dep["status"] == "not_ready" for dep in dependencies):
            status = "not_ready"
            ready = False
        elif any(dep["status"] == "degraded" for dep in dependencies):
            status = "degraded"
            ready = True
        else:
            status = "ready"
            ready = True

        return {
            "status": status,
            "ready": ready,
            "dependencies": dependencies,
        }
