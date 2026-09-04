from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict


class AudioFingerprint:
    """Stable file fingerprint used for duplicate detection.

    This lightweight fallback can later be replaced by Chromaprint/AcoustID
    without changing the ingestion contract.
    """

    def calculate(self, audio_path: str) -> Dict[str, str]:
        path = Path(audio_path)
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return {
            "algorithm": "sha256-file",
            "fingerprint": digest.hexdigest(),
        }
