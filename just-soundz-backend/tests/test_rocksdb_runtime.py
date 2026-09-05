from app.services.rocksdb_runtime import RocksDBRuntime


def test_disabled_runtime_reports_not_ready(monkeypatch, tmp_path):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_PATH", str(tmp_path))
    runtime = RocksDBRuntime()
    result = runtime.preflight()
    assert result["ready"] is False
    assert result["reason"] == "rocksdb_disabled"


def test_tmp_path_is_not_recommended_for_persistent_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_PATH", str(tmp_path))
    runtime = RocksDBRuntime()
    result = runtime.preflight()
    assert result["persistent_path_recommended"] is False


def test_var_lib_path_is_recommended_for_persistent_cache(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_ENABLED", "0")
    monkeypatch.setenv("JUST_MAKER_ROCKSDB_PATH", "/var/lib/just-maker/rocksdb")
    runtime = RocksDBRuntime()
    result = runtime.preflight()
    assert result["persistent_path_recommended"] is True
