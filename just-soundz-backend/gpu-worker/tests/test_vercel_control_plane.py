import importlib.util

from worker import GPUWorker


def test_lightweight_control_plane_reports_runtime_unavailable(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_GPU_MODEL_ID", "example/model")
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    worker = GPUWorker()
    status = worker.status()
    assert status["model_configured"] is True
    assert status["runtime_available"] is False
    assert status["configured"] is False
    assert status["deployment_role"] == "lightweight-control-plane"


def test_gpu_runtime_requires_heavy_dependencies(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_GPU_MODEL_ID", "example/model")
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    worker = GPUWorker()
    try:
        worker.generate({"duration_seconds": 10}, {}, 0)
    except RuntimeError as exc:
        assert "requirements-gpu.txt" in str(exc)
    else:
        raise AssertionError("expected GPU runtime error")
