from app.settings import AppSettings, validate_startup


def test_allowed_origins_are_normalized():
    settings = AppSettings(
        JUST_SOUNDZ_ALLOWED_ORIGINS="https://a.example, https://b.example"
    )
    assert settings.allowed_origins == ["https://a.example", "https://b.example"]


def test_startup_reports_missing_external_worker_without_crashing_dev():
    settings = AppSettings(
        JUST_MAKER_ENVIRONMENT="development",
        JUST_MAKER_REQUIRE_EXTERNAL_GENERATOR=False,
        JUST_SOUNDZ_PRIMARY_WORKER_URL=None,
        JUST_SOUNDZ_MUSICGEN_WORKER_URL=None,
        JUST_SOUNDZ_STABLE_WORKER_URL=None,
    )
    report = validate_startup(settings)
    assert report["valid"] is True
    assert "external_generation_worker" in report["degraded"]


def test_production_can_require_external_generator():
    settings = AppSettings(
        JUST_MAKER_ENVIRONMENT="production",
        JUST_MAKER_REQUIRE_EXTERNAL_GENERATOR=True,
        JUST_SOUNDZ_PRIMARY_WORKER_URL=None,
        JUST_SOUNDZ_MUSICGEN_WORKER_URL=None,
        JUST_SOUNDZ_STABLE_WORKER_URL=None,
    )
    report = validate_startup(settings)
    assert report["valid"] is False
    assert "external_generation_worker" in report["fatal"]
