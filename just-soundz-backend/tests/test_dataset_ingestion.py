from app.music_brain.checkpoints import CheckpointStore
from app.music_brain.sources.musicbrainz import MusicBrainzSource


def test_musicbrainz_normalization_marks_reference_only():
    source = MusicBrainzSource()
    record = source.normalize({
        "id": "abc-123",
        "title": "Test Song",
        "artist-credit": [
            {"artist": {"id": "artist-1", "name": "Test Artist"}}
        ],
        "first-release-date": "1999-01-01",
        "tags": [{"name": "soul"}, {"name": "hip hop"}],
    })

    assert record["external_id"] == "musicbrainz:abc-123"
    assert record["artist_name"] == "Test Artist"
    assert record["release_year"] == 1999
    assert record["rights"]["sampling_allowed"] is False
    assert record["rights"]["status"] == "reference_only"


def test_checkpoint_round_trip(tmp_path):
    store = CheckpointStore(str(tmp_path))
    payload = {"job_id": "job-1", "processed": 50, "status": "running"}
    store.save("job-1", payload)
    assert store.load("job-1") == payload
    store.delete("job-1")
    assert store.load("job-1") is None
