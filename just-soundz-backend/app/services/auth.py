from __future__ import annotations

import os
from typing import Any, Dict, Optional


class SupabaseUserAuth:
    """Validates Supabase access tokens and returns the authenticated user."""

    def __init__(self):
        self.supabase_url = os.getenv("JUST_MAKER_SUPABASE_URL")
        self.publishable_key = (
            os.getenv("JUST_MAKER_SUPABASE_PUBLISHABLE_KEY")
            or os.getenv("JUST_MAKER_SUPABASE_ANON_KEY")
        )

    @property
    def configured(self) -> bool:
        return bool(self.supabase_url and self.publishable_key)

    def get_user(self, authorization: Optional[str]) -> Dict[str, Any]:
        if not self.configured:
            raise RuntimeError("Supabase user auth is not configured")

        if not authorization or not authorization.lower().startswith("bearer "):
            raise PermissionError("Missing bearer token")

        import httpx

        token = authorization.split(" ", 1)[1].strip()
        response = httpx.get(
            f"{self.supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": self.publishable_key,
            },
            timeout=20,
        )

        if response.status_code != 200:
            raise PermissionError("Invalid or expired access token")

        user = response.json()
        user_id = user.get("id")
        if not user_id:
            raise PermissionError("Authenticated user has no id")

        return {
            "id": str(user_id),
            "email": user.get("email"),
            "role": user.get("role"),
            "aud": user.get("aud"),
        }
