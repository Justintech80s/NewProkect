from __future__ import annotations

import os
from urllib.parse import quote
from typing import Any, Dict


class SecureArtifactDelivery:
    """Creates short-lived signed URLs for private Supabase Storage artifacts."""

    def __init__(self):
        self.supabase_url = os.getenv("JUST_MAKER_SUPABASE_URL")
        self.service_role_key = os.getenv("JUST_MAKER_SUPABASE_SERVICE_ROLE_KEY")
        self.default_ttl = int(os.getenv("JUST_MAKER_SIGNED_URL_TTL_SECONDS", "900"))

    @property
    def configured(self) -> bool:
        return bool(self.supabase_url and self.service_role_key)

    def sign(
        self,
        bucket: str,
        object_path: str,
        expires_in: int | None = None,
        download_name: str | None = None,
    ) -> Dict[str, Any]:
        if not self.configured:
            return {
                "signed": False,
                "reason": "artifact_delivery_not_configured",
            }

        import httpx

        ttl = max(60, min(int(expires_in or self.default_ttl), 86400))
        encoded_bucket = quote(bucket, safe="")
        encoded_path = "/".join(quote(part, safe="") for part in object_path.split("/"))
        endpoint = (
            f"{self.supabase_url.rstrip('/')}/storage/v1/object/sign/"
            f"{encoded_bucket}/{encoded_path}"
        )
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {"expiresIn": ttl}
        if download_name:
            payload["download"] = download_name

        response = httpx.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        signed_path = data.get("signedURL") or data.get("signedUrl") or data.get("signed_url")
        if not signed_path:
            raise RuntimeError("Supabase did not return a signed URL")

        if signed_path.startswith("http"):
            signed_url = signed_path
        else:
            signed_url = f"{self.supabase_url.rstrip('/')}/storage/v1{signed_path}"

        return {
            "signed": True,
            "signed_url": signed_url,
            "expires_in": ttl,
            "bucket": bucket,
            "object_path": object_path,
        }
