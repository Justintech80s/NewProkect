from app.services.local_cache import RocksLocalCache


def test_clear_is_safe_when_cache_disabled(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    cache = RocksLocalCache("music-brain-search")
    assert cache.clear() == 0


def test_delete_prefix_is_safe_when_cache_disabled(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    cache = RocksLocalCache("music-brain-search")
    assert cache.delete_prefix("search:") == 0
