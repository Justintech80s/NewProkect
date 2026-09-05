import os

from worker import GPUWorker


def test_gpu_worker_exposes_expected_capabilities(monkeypatch, tmp_path):
    monkeypatch.setenv("JUST_MAKER_GPU_MODEL_ID", "test-model")
    monkeypatch.setenv("JUST_MAKER_GPU_OUTPUT_DIR", str(tmp_path))
    worker = GPUWorker()

    capabilities = worker.capabilities()

    assert capabilities["text_prompt"] is True
    assert capabilities["bpm"] is True
    assert capabilities["key"] is True
    assert capabilities["rhythm_conditioning"] is True
    assert capabilities["stem_conditioning"] is True


def test_gpu_worker_status_does_not_load_model(monkeypatch, tmp_path):
    monkeypatch.setenv("JUST_MAKER_GPU_MODEL_ID", "test-model")
    monkeypatch.setenv("JUST_MAKER_GPU_OUTPUT_DIR", str(tmp_path))
    worker = GPUWorker()

    status = worker.status()

    assert status["configured"] is True
    assert status["loaded"] is False
