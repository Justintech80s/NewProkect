from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import AppError, register_error_handlers
from app.main import app


client = TestClient(app)


def test_validation_error_has_stable_envelope():
    response = client.post(
        "/v1/generate",
        json={"prompt": "x", "duration_seconds": 1},
    )
    error = response.json()["error"]
    assert response.status_code == 422
    assert error["code"] == "validation_error"
    assert error["request_id"]
    assert error["retryable"] is False


def test_not_found_has_stable_envelope():
    response = client.get("/does-not-exist")
    error = response.json()["error"]
    assert response.status_code == 404
    assert error["code"] == "not_found"
    assert error["request_id"]


def test_missing_authentication_has_stable_envelope():
    response = client.get("/v1/me")
    assert response.status_code in {401, 503}
    error = response.json()["error"]
    assert error["code"] in {"authentication_required", "service_unavailable"}
    assert error["request_id"]


def test_synthetic_retryable_app_error():
    synthetic = FastAPI()
    register_error_handlers(synthetic)

    @synthetic.get("/unavailable")
    def unavailable():
        raise AppError(
            code="generator_unavailable",
            message="Music generation is temporarily unavailable.",
            status_code=503,
            retryable=True,
        )

    response = TestClient(synthetic).get("/unavailable")
    error = response.json()["error"]
    assert response.status_code == 503
    assert error["code"] == "generator_unavailable"
    assert error["retryable"] is True
    assert error["request_id"]
