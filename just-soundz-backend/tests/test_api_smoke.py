import uuid

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_contract():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["service"] == "just-maker-ai-backend"
    assert payload["version"]


def test_request_id_is_generated_and_echoed():
    response = client.get("/health")
    request_id = response.headers["X-Request-ID"]
    uuid.UUID(request_id)


def test_valid_request_id_is_preserved():
    response = client.get("/health", headers={"X-Request-ID": "site-req-123"})
    assert response.headers["X-Request-ID"] == "site-req-123"


def test_root_exposes_core_pipeline():
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    pipeline = payload["pipeline"]

    for stage in (
        "music-brain-retrieval",
        "producer-dna",
        "gpu-model-worker",
        "automated-evaluation",
        "worker-circuit-breakers",
    ):
        assert stage in pipeline


def test_authenticated_job_endpoint_rejects_missing_token_with_safe_error():
    response = client.post(
        "/v1/jobs",
        json={
            "prompt": "original cinematic hip hop instrumental",
            "duration_seconds": 60,
        },
    )
    assert response.status_code in {401, 503}
    error = response.json()["error"]
    assert error["request_id"]
    assert isinstance(error["retryable"], bool)
