from app.services.local_cache import RocksLocalCache


def test_disabled_cache_is_safe_noop(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    cache = RocksLocalCache("test")
    assert cache.available is False
    assert cache.get("missing") is None
    assert cache.set("x", {"a": 1}) is False


def test_cache_key_is_deterministic(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    cache = RocksLocalCache("test")
    first = cache.make_key("search", {"q": "hip hop", "limit": 20})
    second = cache.make_key("search", {"limit": 20, "q": "hip hop"})
    assert first == second


def test_status_keeps_postgres_authoritative(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    cache = RocksLocalCache("test")
    assert cache.status()["authoritative_store"] == "supabase-postgres"
