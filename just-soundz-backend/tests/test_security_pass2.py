import uuid

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.jobs import JobStore
from app.ownership import owned_job
from app.security import normalize_uuid, safe_download_name, validate_storage_path
from app.services.artifact_delivery import (
    MAX_SIGNED_URL_TTL_SECONDS,
    MIN_SIGNED_URL_TTL_SECONDS,
    SecureArtifactDelivery,
)
from app.services.usage import UsageQuotaService


class DurableFake:
    def __init__(self, configured=False, records=None):
        self.configured = configured
        self.records = records or {}

    def get(self, job_id, user_id=None):
        record = self.records.get(job_id)
        if not record or record.get("user_id") != user_id:
            return None
        return dict(record)


def test_owned_job_in_memory_is_user_isolated():
    store = JobStore()
    owner = str(uuid.uuid4())
    other = str(uuid.uuid4())
    job = store.create(user_id=owner)
    assert owned_job(job.id, owner, durable_store=DurableFake(), memory_store=store)
    assert owned_job(job.id, other, durable_store=DurableFake(), memory_store=store) is None


def test_owned_job_uses_durable_store_when_configured():
    owner = str(uuid.uuid4())
    other = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    durable = DurableFake(True, {job_id: {"job_id": job_id, "user_id": owner, "status": "queued"}})
    assert owned_job(job_id, owner, durable_store=durable, memory_store=JobStore())
    assert owned_job(job_id, other, durable_store=durable, memory_store=JobStore()) is None


def test_malformed_identifier_is_rejected():
    with pytest.raises(ValueError):
        normalize_uuid("../../etc/passwd")


@pytest.mark.parametrize("value", ["../master.wav", "/tmp/x.wav", "folder/../../x.wav", "a\\b.wav"])
def test_unsafe_download_names_are_rejected(value):
    with pytest.raises(ValueError):
        safe_download_name(value)


@pytest.mark.parametrize("value", ["../secret/file.wav", "/absolute/file.wav", "a/../b.wav"])
def test_unsafe_storage_paths_are_rejected(value):
    with pytest.raises(ValueError):
        validate_storage_path(value)


def test_signed_url_ttl_is_strictly_bounded():
    service = SecureArtifactDelivery()
    assert MIN_SIGNED_URL_TTL_SECONDS <= service.default_ttl <= MAX_SIGNED_URL_TTL_SECONDS
    assert MAX_SIGNED_URL_TTL_SECONDS <= 3600


def test_concurrency_limit_blocks_authenticated_generation(monkeypatch):
    service = UsageQuotaService()
    monkeypatch.setattr(
        service,
        "status",
        lambda user_id: {
            "configured": True,
            "allowed": False,
            "suspended": False,
            "limits": {"daily_jobs": 20, "monthly_seconds": 7200, "concurrent_jobs": 2},
            "usage": {"daily_jobs": 1, "monthly_seconds": 100, "concurrent_jobs": 2},
            "remaining": {"daily_jobs": 19, "monthly_seconds": 7100, "concurrent_jobs": 0},
        },
    )
    result = service.check(str(uuid.uuid4()), 60)
    assert result["allowed"] is False
    assert "concurrent_job_limit_reached" in result["reasons"]


client = TestClient(main_module.app)


def test_security_headers_are_attached():
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_auth_provider_failure_does_not_leak_internal_details(monkeypatch):
    def explode(_authorization):
        raise RuntimeError("super-secret-provider-token-123")

    monkeypatch.setattr(main_module.user_auth, "get_user", explode)
    response = client.get("/v1/me", headers={"Authorization": "Bearer secret-user-token"})
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "service_unavailable"
    rendered = str(body)
    assert "super-secret-provider-token-123" not in rendered
    assert "secret-user-token" not in rendered


def test_cross_user_in_memory_job_access_is_404(monkeypatch):
    owner = str(uuid.uuid4())
    other = str(uuid.uuid4())
    job = main_module.jobs.create(user_id=owner)
    monkeypatch.setattr(
        main_module.user_auth,
        "get_user",
        lambda authorization: {"id": other, "email": None, "role": "authenticated", "aud": "authenticated"},
    )
    response = client.get(
        f"/v1/jobs/{job.id}",
        headers={"Authorization": "Bearer opaque"},
    )
    assert response.status_code == 404


def test_malformed_job_id_is_404_not_database_error(monkeypatch):
    user_id = str(uuid.uuid4())
    monkeypatch.setattr(
        main_module.user_auth,
        "get_user",
        lambda authorization: {"id": user_id, "email": None, "role": "authenticated", "aud": "authenticated"},
    )
    response = client.get(
        "/v1/jobs/not-a-uuid",
        headers={"Authorization": "Bearer opaque"},
    )
    assert response.status_code == 404
