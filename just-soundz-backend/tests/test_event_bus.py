from app.services.event_bus import EventOutbox, KafkaEventBus


def test_kafka_bus_gracefully_falls_back_when_not_configured(monkeypatch):
    monkeypatch.delenv("JUST_MAKER_KAFKA_BOOTSTRAP_SERVERS", raising=False)
    bus = KafkaEventBus(EventOutbox())
    bus.outbox.database_url = None

    result = bus.emit(
        "justmaker.jobs",
        "generation.queued",
        {"job_id": "abc"},
        key="abc",
    )

    assert result["published"] is False
    assert result["reason"] == "kafka_not_configured"


def test_outbox_envelope_contains_event_metadata(monkeypatch):
    outbox = EventOutbox()
    outbox.database_url = None

    result = outbox.enqueue(
        "justmaker.jobs",
        "generation.started",
        {"job_id": "abc"},
        key="abc",
    )

    assert result["envelope"]["event_type"] == "generation.started"
    assert result["envelope"]["source"] == "just-maker-backend"
    assert result["envelope"]["payload"]["job_id"] == "abc"
