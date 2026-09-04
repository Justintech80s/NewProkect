from app.services.usage import UsageQuotaService


def test_unconfigured_usage_service_allows_requests(monkeypatch):
    monkeypatch.delenv("JUST_MAKER_DATABASE_URL", raising=False)
    service = UsageQuotaService()
    result = service.check("00000000-0000-0000-0000-000000000001", 120)
    assert result["allowed"] is True


def test_default_limits_are_positive(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_DAILY_JOB_LIMIT", "20")
    monkeypatch.setenv("JUST_MAKER_MONTHLY_SECONDS_LIMIT", "7200")
    monkeypatch.setenv("JUST_MAKER_CONCURRENT_JOB_LIMIT", "2")
    service = UsageQuotaService()
    assert service.default_daily_jobs == 20
    assert service.default_monthly_seconds == 7200
    assert service.default_concurrent_jobs == 2
