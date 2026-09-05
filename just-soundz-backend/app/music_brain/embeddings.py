from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import List


class MusicEmbeddingEngine:
    """Embedding facade.

    Production can connect CLAP or another licensed embedding service. The
    deterministic fallback keeps development/search contracts testable.
    """

    dimension = 512

    def text_embedding(self, text: str) -> List[float]:
        try:
            return self._remote_text_embedding(text)
        except Exception:
            return self._fallback(text.encode("utf-8"))

    def audio_embedding(self, audio_path: str) -> List[float]:
        try:
            return self._remote_audio_embedding(audio_path)
        except Exception:
            payload = Path(audio_path).read_bytes()
            return self._fallback(payload)

    def _remote_text_embedding(self, text: str) -> List[float]:
        import os
        import httpx

        url = os.getenv("JUST_MAKER_EMBEDDING_URL")
        if not url:
            raise RuntimeError("embedding service not configured")
        token = os.getenv("JUST_MAKER_EMBEDDING_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = httpx.post(
            url.rstrip("/") + "/embed/text",
            json={"text": text},
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        values = response.json()["embedding"]
        return [float(v) for v in values]

    def _remote_audio_embedding(self, audio_path: str) -> List[float]:
        import os
        import httpx

        url = os.getenv("JUST_MAKER_EMBEDDING_URL")
        if not url:
            raise RuntimeError("embedding service not configured")
        token = os.getenv("JUST_MAKER_EMBEDDING_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        path = Path(audio_path)
        with path.open("rb") as handle:
            response = httpx.post(
                url.rstrip("/") + "/embed/audio",
                files={"audio": (path.name, handle, "audio/wav")},
                headers=headers,
                timeout=120,
            )
        response.raise_for_status()
        values = response.json()["embedding"]
        return [float(v) for v in values]

    def _fallback(self, payload: bytes) -> List[float]:
        values = []
        seed = payload
        while len(values) < self.dimension:
            seed = hashlib.sha256(seed).digest()
            values.extend((b - 127.5) / 127.5 for b in seed)
        values = values[: self.dimension]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]
