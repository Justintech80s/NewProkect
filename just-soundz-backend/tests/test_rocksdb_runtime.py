from app.services.rocksdb_runtime import RocksDBRuntime


def test_disabled_runtime_reports_not_ready(monkeypatch, tmp_path):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_PATH", str(tmp_path))
    runtime = RocksDBRuntime()
    result = runtime.preflight()
    assert result["ready"] is False
    assert result["reason"] == "rocksdb_disabled"


def test_persistent_path_recommendation(monkeypatch, tmp_path):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_PATH", str(tmp_path))
    runtime = RocksDBRuntime()
    result = runtime.preflight()
    assert result["persistent_path_recommended"] is True
