import os

from app.services.model_registry import ModelRegistry
from app.services.worker_selector import WorkerSelector


def test_dynamic_ensemble_workers_are_registered(monkeypatch):
    monkeypatch.setenv(
        "JUST_MAKER_ENSEMBLE_WORKERS",
        "hiphop-gpu|http-worker|TEST_HIPHOP_URL|TEST_HIPHOP_TOKEN|12;"
        "cinematic-gpu|stable-audio-worker|TEST_CINEMATIC_URL|TEST_CINEMATIC_TOKEN|14",
    )
    monkeypatch.setenv("TEST_HIPHOP_URL", "https://hiphop.invalid")
    monkeypatch.setenv("TEST_CINEMATIC_URL", "https://cinematic.invalid")
    names = {worker.name for worker in ModelRegistry().workers()}
    assert "hiphop-gpu" in names
    assert "cinematic-gpu" in names


def test_invalid_ensemble_specs_are_ignored(monkeypatch):
    monkeypatch.setenv(
        "JUST_MAKER_ENSEMBLE_WORKERS",
        "bad-spec;evil|unsupported-kind|URL|TOKEN|1",
    )
    names = {worker.name for worker in ModelRegistry().workers()}
    assert "evil" not in names


def test_genre_specialization_bonus(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_HIPHOP_GPU_GENRES", "hip-hop,boom-bap")
    selector = WorkerSelector()
    assert selector._specialization_bonus("hiphop-gpu", "hip-hop") == 0.08
    assert selector._specialization_bonus("hiphop-gpu", "ambient") == 0.0
