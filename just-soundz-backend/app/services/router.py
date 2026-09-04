import os
from typing import Dict, Any

class GenerationRouter:
    """
    Provider-agnostic generation layer.

    Configure commercial/approved providers through environment variables.
    Optional local adapters can be added for JASCO/MusicGen-compatible or
    Stable Audio-compatible workers without changing the frontend API.
    """

    def __init__(self):
        self.provider = os.getenv("JUST_SOUNDZ_GENERATOR", "disabled")

    def generate(self, plan: Dict[str, Any], variation: int = 0):
        if self.provider == "disabled":
            return {
                "provider": "disabled",
                "audio_path": None,
                "message": (
                    "Generation architecture is installed, but no commercial or "
                    "approved music-model provider is configured yet."
                ),
            }

        if self.provider == "http-worker":
            return self._http_worker(plan, variation)

        return {
            "provider": self.provider,
            "audio_path": None,
            "message": f"Unknown JUST_SOUNDZ_GENERATOR provider: {self.provider}",
        }

    def _http_worker(self, plan, variation):
        # Deliberately leaves model choice outside the web app so GPU/music models
        # can be swapped without changing the frontend.
        import httpx
        url = os.environ["JUST_SOUNDZ_WORKER_URL"].rstrip("/") + "/generate"
        token = os.getenv("JUST_SOUNDZ_WORKER_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        payload = {"plan": plan, "variation": variation}
        r = httpx.post(url, json=payload, headers=headers, timeout=600)
        r.raise_for_status()
        data = r.json()
        return {
            "provider": "http-worker",
            "audio_path": data.get("audio_path"),
            "metadata": data.get("metadata", {}),
        }
