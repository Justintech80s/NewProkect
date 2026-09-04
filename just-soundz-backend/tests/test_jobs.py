from app.jobs import JobStore


def test_job_lifecycle():
    store = JobStore()
    job = store.create()
    assert job.status == "queued"

    store.update(job.id, status="complete", result={"ok": True})
    updated = store.get(job.id)

    assert updated is not None
    assert updated.status == "complete"
    assert updated.result == {"ok": True}
