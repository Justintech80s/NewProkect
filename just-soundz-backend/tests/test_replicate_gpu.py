from app.services.model_registry import ModelRegistry
from app.services.providers import ReplicateDeploymentProvider


def test_replicate_worker_registers_when_configured(monkeypatch):
    monkeypatch.setenv("JUST_SOUNDZ_REPLICATE_DEPLOYMENT", "owner/just-maker-gpu")
    monkeypatch.setenv("JUST_SOUNDZ_REPLICATE_API_TOKEN", "secret")
    workers = ModelRegistry().workers()
    replicate = next(worker for worker in workers if worker.name == "replicate-gpu")
    assert replicate.kind == "replicate-deployment"
    assert replicate.url == "owner/just-maker-gpu"
    assert replicate.priority == 5


def test_replicate_output_url_supports_file_shapes():
    fn = ReplicateDeploymentProvider._output_url
    assert fn("https://example.test/output.wav") == "https://example.test/output.wav"
    assert fn(["https://example.test/output.wav"]) == "https://example.test/output.wav"
    assert fn({"audio": "https://example.test/output.wav"}) == "https://example.test/output.wav"
    assert fn(None) is None


def test_replicate_deployment_identifier_validation():
    provider = ReplicateDeploymentProvider("owner/deployment", "secret")
    assert provider._deployment_url().endswith(
        "/v1/deployments/owner/deployment"
    )


def test_replicate_worker_not_registered_without_deployment(monkeypatch):
    monkeypatch.delenv("JUST_SOUNDZ_REPLICATE_DEPLOYMENT", raising=False)
    names = {worker.name for worker in ModelRegistry().workers()}
    assert "replicate-gpu" not in names
