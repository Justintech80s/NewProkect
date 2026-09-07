import uuid

from app.request_context import normalize_request_id


def test_missing_id_becomes_uuid4_shape():
    value = normalize_request_id(None)
    uuid.UUID(value)


def test_control_character_id_is_replaced():
    value = normalize_request_id("bad\nheader")
    assert "\n" not in value
    assert len(value) == 36


def test_oversized_id_is_replaced():
    value = normalize_request_id("x" * 500)
    assert len(value) == 36


def test_valid_caller_id_is_preserved():
    assert normalize_request_id("site-req-123") == "site-req-123"
