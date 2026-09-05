from app.services.cache_tuner import AdaptiveCacheTuner


def test_high_hit_rate_extends_ttl(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ADAPTIVE_CACHE_TTL", "1")
    tuner = AdaptiveCacheTuner()
    result = tuner.recommend(
        {"hits": 90, "misses": 10, "writes": 50, "invalidated": 5, "errors": 0},
        namespace="music-brain-search",
        base_ttl=600,
    )
    assert result["recommended_ttl_seconds"] > 600


def test_high_churn_shortens_ttl(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ADAPTIVE_CACHE_TTL", "1")
    tuner = AdaptiveCacheTuner()
    result = tuner.recommend(
        {"hits": 60, "misses": 40, "writes": 20, "invalidated": 20, "errors": 0},
        namespace="music-brain-search",
        base_ttl=900,
    )
    assert result["recommended_ttl_seconds"] < 900


def test_ttl_respects_bounds(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ADAPTIVE_CACHE_TTL", "1")
    monkeypatch.setenv("JUST_MAKER_CACHE_MIN_TTL_SECONDS", "120")
    monkeypatch.setenv("JUST_MAKER_CACHE_MAX_TTL_SECONDS", "1000")
    tuner = AdaptiveCacheTuner()
    result = tuner.recommend(
        {"hits": 1000, "misses": 1, "writes": 100, "invalidated": 0, "errors": 0},
        namespace="x",
        base_ttl=900,
    )
    assert result["recommended_ttl_seconds"] <= 1000
