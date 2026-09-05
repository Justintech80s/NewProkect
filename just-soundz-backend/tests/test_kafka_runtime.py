from app.services.kafka_runtime import KafkaRuntime


def test_runtime_not_configured_is_safe(monkeypatch):
    monkeypatch.delenv("JUST_MAKER_KAFKA_BOOTSTRAP_SERVERS", raising=False)
    runtime = KafkaRuntime()
    result = runtime.health()
    assert result["configured"] is False
    assert result["connected"] is False


def test_required_topics_include_pipeline_topics(monkeypatch):
    monkeypatch.delenv("JUST_MAKER_KAFKA_BOOTSTRAP_SERVERS", raising=False)
    runtime = KafkaRuntime()
    names = {item["name"] for item in runtime.required_topics()}
    assert "justmaker.jobs" in names
    assert "justmaker.gpu.requests" in names
    assert "justmaker.gpu.results" in names
    assert "justmaker.cache" in names
    assert "justmaker.dead-letter" in names


def test_topic_partitions_are_positive(monkeypatch):
    monkeypatch.setenv("JUST_MAKER_KAFKA_DEFAULT_PARTITIONS", "6")
    runtime = KafkaRuntime()
    assert all(item["partitions"] >= 1 for item in runtime.required_topics())
