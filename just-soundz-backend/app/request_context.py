from __future__ import annotations

import uuid


REQUEST_ID_HEADER = "X-Request-ID"


def normalize_request_id(value: str | None) -> str:
    if value is not None:
        candidate = value.strip()
        if 1 <= len(candidate) <= 128 and all(32 <= ord(ch) <= 126 for ch in candidate):
            return candidate
    return str(uuid.uuid4())
