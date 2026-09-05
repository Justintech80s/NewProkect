from __future__ import annotations

from typing import Any, Dict


class ReadinessChecker:
    def __init__(self, *, database, router, artifact_store, user_auth):
        self.database = database
        self.router = router
        self.artifact_store = artifact_store
        self.user_auth = user_auth

    def check(self) -> Dict[str, Any]:
        checks = {
            "database_configured": bool(self.database.configured),
            "generation_worker_available": bool(
                any(
                    w.get("configured")
                    for w in self.router.status().get("workers", [])
                )
            ),
            "artifact_storage_configured": bool(self.artifact_store.configured),
            "user_auth_configured": bool(self.user_auth.configured),
        }

        critical = [
            checks["database_configured"],
            checks["generation_worker_available"],
        ]
        return {
            "ready": all(critical),
            "checks": checks,
        }
