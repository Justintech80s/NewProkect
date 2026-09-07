import pytest

import app.main as main_module
from app.jobs import JobStore, jobs
from app.services.job_states import JobStateError


def test_job_lifecycle():
    store = JobStore()
    job = store.create()
    assert job.status == "queued"

    store.update(job.id, status="running")
    store.update(job.id, status="complete", result={"ok": True})
    updated = store.get(job.id)

    assert updated is not None
    assert updated.status == "complete"
    assert updated.result == {"ok": True}


def test_duplicate_complete_is_idempotent():
    store = JobStore()
    job = store.create()
    store.update(job.id, status="running")
    store.update(job.id, status="complete")
    store.update(job.id, status="complete")
    assert store.get(job.id).status == "complete"


def test_complete_cannot_return_to_running():
    store = JobStore()
    job = store.create()
    store.update(job.id, status="running")
    store.update(job.id, status="complete")
    with pytest.raises(JobStateError):
        store.update(job.id, status="running")


def test_unknown_job_field_is_rejected():
    store = JobStore()
    job = store.create()
    with pytest.raises(ValueError):
        store.update(job.id, mystery=True)


def test_process_job_failure_cannot_leave_running(monkeypatch):
    job = jobs.create(user_id="00000000-0000-0000-0000-000000000001")

    def explode(*args, **kwargs):
        raise RuntimeError("synthetic generation failure")

    monkeypatch.setattr(main_module, "run_generation", explode)
    main_module.process_job(
        job.id,
        main_module.GenerateRequest(prompt="original test beat"),
        user_id=job.user_id,
        request_id="req-test-failure",
    )
    updated = jobs.get(job.id)
    assert updated is not None
    assert updated.status == "failed"
    assert updated.request_id == "req-test-failure"
