from datetime import datetime, timedelta, timezone

import pytest

from app.services.job_recovery import JobRecoveryPlanner
from app.services.job_states import JobStateError, normalize_progress, validate_transition


def test_running_to_running_is_idempotent():
    assert validate_transition("running", "running") == "running"


def test_complete_cannot_return_to_running():
    with pytest.raises(JobStateError):
        validate_transition("complete", "running")


def test_unknown_state_is_rejected():
    with pytest.raises(JobStateError):
        validate_transition("queued", "stalled")


def test_complete_progress_is_one():
    assert normalize_progress("complete", 0.2) == 1.0


def test_stale_running_job_is_retryable_without_fifth_state():
    planner = JobRecoveryPlanner(stale_after_seconds=60)
    old = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    result = planner.assess({
        "status": "running",
        "heartbeat_at": old,
        "retry_count": 0,
        "max_retries": 3,
    })
    assert result["retryable"] is True
    assert result["reason"] == "stale_running_job"


def test_fresh_running_job_is_not_retryable():
    planner = JobRecoveryPlanner(stale_after_seconds=60)
    result = planner.assess({
        "status": "running",
        "heartbeat_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": 0,
        "max_retries": 3,
    })
    assert result["retryable"] is False


def test_failed_job_is_retryable_until_limit():
    planner = JobRecoveryPlanner()
    result = planner.assess({"status": "failed", "retry_count": 1, "max_retries": 3})
    assert result["retryable"] is True
