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


def test_authenticated_job_endpoint_rejects_missing_token():
    response = client.post(
        "/v1/jobs",
        json={
            "prompt": "original cinematic hip hop instrumental",
            "duration_seconds": 60,
        },
    )
    assert response.status_code in {401, 503}
