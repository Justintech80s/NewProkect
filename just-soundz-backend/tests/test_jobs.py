import pytest

from app.jobs import JobStore
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
