from app.services.job_recovery import JobRecoveryPlanner


def test_failed_job_is_retryable_before_limit():
    planner = JobRecoveryPlanner()
    result = planner.assess({
        "status": "failed",
        "retry_count": 1,
        "max_retries": 3,
    })
    assert result["retryable"] is True


def test_retry_limit_blocks_job():
    planner = JobRecoveryPlanner()
    result = planner.assess({
        "status": "failed",
        "retry_count": 3,
        "max_retries": 3,
    })
    assert result["retryable"] is False
