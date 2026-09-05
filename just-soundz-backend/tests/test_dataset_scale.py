from app.music_brain.dataset_manifest import DatasetManifest
from app.music_brain.dataset_quality import DatasetQualityGate


def test_metadata_manifest_does_not_grant_sampling_rights():
    record = {"external_id": "x:1", "title": "Song", "artist_name": "Artist"}
    out = DatasetManifest(source_name="catalog").apply(record)
    assert out["rights"]["sampling_allowed"] is False
    assert out["rights"]["commercial_use"] is False
    assert out["rights"]["status"] == "reference_only"


def test_quality_gate_rejects_bad_numeric_metadata():
    gate = DatasetQualityGate()
    result = gate.validate({
        "external_id": "x:2",
        "title": "Song",
        "artist_name": "Artist",
        "bpm": 900,
        "release_year": 1200,
    })
    assert result["valid"] is False
    assert "invalid_bpm" in result["errors"]
    assert "invalid_release_year" in result["errors"]


def test_fingerprint_is_stable():
    gate = DatasetQualityGate()
    a = {"external_id": "X:3", "title": " Song ", "artist_name": "ARTIST"}
    b = {"external_id": "x:3", "title": "song", "artist_name": "artist"}
    assert gate.fingerprint(a) == gate.fingerprint(b)
