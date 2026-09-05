from pathlib import Path


def test_gpu_kafka_consumer_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / "gpu-worker" / "kafka_consumer.py").exists()


def test_kafka_architecture_keeps_rocksdb_deferred():
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "KAFKA_ARCHITECTURE.md").read_text()
    assert "RocksDB is intentionally not enabled" in text
    assert "Supabase/Postgres remains the system of record" in text
