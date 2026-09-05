from app.services.local_cache import RocksLocalCache


def test_disabled_get_records_cache_miss(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    cache = RocksLocalCache("test")
    assert cache.get("missing") is None
    assert cache.metrics()["misses"] == 1
    assert cache.metrics()["hit_rate"] == 0.0


def test_metrics_expose_operational_counters(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    cache = RocksLocalCache("test")
    metrics = cache.metrics()
    assert set(["hits", "misses", "writes", "invalidated", "errors", "hit_rate"]).issubset(metrics)
