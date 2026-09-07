from __future__ import annotations

import re
import uuid
from pathlib import PurePosixPath

PUBLIC_ENDPOINTS = {
    ("GET", "/"),
    ("GET", "/health"),
    ("GET", "/ready"),
    ("GET", "/v1/generation-workers"),
    ("GET", "/v1/music-brain/status"),
    ("POST", "/v1/music-brain/search"),
    ("POST", "/v1/music-brain/rights/check"),
    ("POST", "/v1/render"),
    ("POST", "/v1/generate"),
}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,127}$")


def normalize_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("invalid_identifier") from exc


def safe_download_name(value: str | None) -> str | None:
    if value is None:
        return None
    name = value.strip()
    if (
        not _SAFE_FILENAME.fullmatch(name)
        or "/" in name
        or "\\" in name
        or name in {".", ".."}
    ):
        raise ValueError("unsafe_filename")
    return name


def validate_storage_path(value: str) -> str:
    if not value or value.startswith("/"):
        raise ValueError("unsafe_storage_path")
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("unsafe_storage_path")
    return str(path)


def apply_security_headers(response) -> None:
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
