from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.music_brain.audio_intelligence import AudioIntelligenceEngine
from app.music_brain.batch import DatasetBatchIngestor
from app.music_brain.dataset_manifest import DatasetManifest
from app.music_brain.dataset_quality import DatasetQualityGate
from app.music_brain.ingestion import MusicIngestionPipeline
from app.music_brain.intelligence import DatasetIntelligence
from app.music_brain.rights import SampleRightsEngine
from app.music_brain.search import MusicBrainSearch


def record(**overrides):
    base = {
        "external_id": "fixture-1",
        "title": "Fixture Song",
        "artist_name": "Fixture Artist",
        "release_year": 1998,
        "bpm": 92,
        "musical_key": "C minor",
        "genres": ["Hip Hop", "hip   hop", "Soul"],
        "mood": ["moody"],
        "instruments": ["drums", "bass"],
        "metadata": {
            "provenance": {
                "source_name": "fixture",
                "license_name": "fixture terms",
                "metadata_only": True,
            }
        },
        "rights": {
            "status": "reference_only",
            "sampling_allowed": False,
            "commercial_use": False,
        },
    }
    base.update(overrides)
    return base


def test_dataset_quality_rejects_impossible_and_unsafe_records():
    gate = DatasetQualityGate()
    result = gate.validate(
        record(
            bpm=float("nan"),
            rights={
                "status": "copyrighted",
                "sampling_allowed": True,
                "commercial_use": True,
            },
        )
    )
    assert result["valid"] is False
    assert "invalid_bpm" in result["errors"]
    assert "sampling_not_supported_by_rights_status" in result["errors"]
    assert "commercial_use_not_supported_by_rights_status" in result["errors"]


def test_dataset_manifest_never_promotes_metadata_to_sampleable():
    manifest = DatasetManifest(source_name="metadata-source", metadata_only=True)
    applied = manifest.apply(
        {
            "external_id": "x",
            "title": "X",
            "artist_name": "Y",
        }
    )
    assert applied["rights"]["status"] == "reference_only"
    assert applied["rights"]["sampling_allowed"] is False
    assert applied["rights"]["commercial_use"] is False


def test_rights_engine_requires_explicit_clearance():
    engine = SampleRightsEngine()
    denied = engine.evaluate(
        {
            "status": "licensed",
            "sampling_allowed": False,
            "commercial_use": True,
        }
    )
    allowed = engine.evaluate(
        {
            "status": "licensed",
            "sampling_allowed": True,
            "commercial_use": True,
        }
    )
    assert denied["eligible_for_automatic_sampling"] is False
    assert allowed["eligible_for_automatic_sampling"] is True


def test_embedding_validation_normalizes_and_rejects_bad_vectors():
    intelligence = DatasetIntelligence()
    normalized = intelligence.validate_embedding([3.0, 4.0], expected_dimension=2)
    assert math.isclose(sum(v * v for v in normalized), 1.0, rel_tol=1e-6)

    with pytest.raises(ValueError, match="invalid_embedding_dimension"):
        intelligence.validate_embedding([1.0], expected_dimension=2)
    with pytest.raises(ValueError, match="non_finite_embedding"):
        intelligence.validate_embedding([1.0, float("nan")], expected_dimension=2)
    with pytest.raises(ValueError, match="zero_embedding"):
        intelligence.validate_embedding([0.0, 0.0], expected_dimension=2)


def test_tag_normalization_is_deterministic_and_deduplicated():
    intelligence = DatasetIntelligence()
    assert intelligence.normalize_tags(
        [" Hip   Hop ", "hip hop", "SOUL", "", "soul"]
    ) == ["hip hop", "soul"]


def test_retrieval_ranking_is_deterministic_and_rights_aware():
    intelligence = DatasetIntelligence()
    rows = [
        {
            "id": 2,
            "external_id": "b",
            "similarity": 0.9,
            "bpm": 90,
            "genres": ["hip hop"],
            "sampling_allowed": False,
            "commercial_use": False,
            "rights_status": "reference_only",
        },
        {
            "id": 1,
            "external_id": "a",
            "similarity": 0.8,
            "bpm": 90,
            "key": "Cm",
            "genres": ["hip hop"],
            "mood": ["dark"],
            "instruments": ["drums"],
            "sampling_allowed": True,
            "commercial_use": True,
            "rights_status": "licensed",
        },
    ]
    all_rows = intelligence.rerank(
        rows,
        sample_eligible_only=False,
        limit=20,
    )
    eligible = intelligence.rerank(
        rows,
        sample_eligible_only=True,
        limit=20,
    )
    assert len(all_rows) == 2
    assert [row["external_id"] for row in eligible] == ["a"]
    assert all_rows == intelligence.rerank(
        rows,
        sample_eligible_only=False,
        limit=20,
    )


class FakeDB:
    configured = True

    def semantic_search_with_profiles(self, embedding, limit=20):
        return [
            {
                "id": 1,
                "external_id": "ref-1",
                "title": "Reference",
                "artist": "Artist",
                "bpm": 94,
                "key": "Dm",
                "genres": ["hip hop"],
                "mood": ["dark"],
                "instruments": ["drums"],
                "similarity": 0.82,
                "production_profile": {
                    "era": "1990s",
                    "tempo_bucket": "midtempo",
                    "energy": 0.6,
                    "harmonic_complexity": 0.5,
                    "bass_prominence": 0.7,
                    "sample_chop_intensity": 0.8,
                },
            }
        ]

    def semantic_sample_search(self, embedding, limit=20):
        return [
            {
                "id": 9,
                "external_id": "sample-1",
                "title": "Cleared",
                "artist": "Artist",
                "bpm": 94,
                "key": "Dm",
                "genres": ["hip hop"],
                "mood": ["dark"],
                "instruments": ["drums"],
                "similarity": 0.75,
                "sampling_allowed": True,
                "commercial_use": True,
                "rights_status": "licensed",
            }
        ]


class FakeEmbeddings:
    dimension = 2

    def text_embedding(self, _text):
        return [1.0, 0.0]


class FakeGraph:
    configured = False


class FakeRelational:
    configured = False

    def related_songs(self, song_id, limit=20):
        return []


class FakeCache:
    namespace = "fixture"
    default_ttl = 60

    def __init__(self):
        self.value = None

    def make_key(self, *args, **kwargs):
        return "key"

    def get(self, key):
        return self.value

    def set(self, key, value, ttl_seconds):
        self.value = value

    def status(self):
        return {"backend": "fixture"}

    def metrics(self):
        return {}


class FakeTuner:
    def ttl_for(self, cache):
        return 60

    def recommend(self, *args, **kwargs):
        return {"ttl_seconds": 60}


def test_music_brain_search_exposes_auditable_ranking():
    search = MusicBrainSearch()
    search.db = FakeDB()
    search.embeddings = FakeEmbeddings()
    search.graph = FakeGraph()
    search.relational_graph = FakeRelational()
    search.cache = FakeCache()
    search.cache_tuner = FakeTuner()

    result = search.search("dark boom bap", limit=10)
    assert result["results"][0]["retrieval_score"] > 0
    assert result["retrieval"]["ranking"] == "pass4-v1"
    assert len(result["retrieval"]["context_fingerprint"]) == 16


def test_batch_ingestion_deduplicates_and_reports_confidence(monkeypatch):
    ingestor = DatasetBatchIngestor()
    monkeypatch.setattr(
        ingestor.pipeline,
        "ingest",
        lambda candidate: {"database": {"stored": True}},
    )
    monkeypatch.setattr(ingestor.checkpoints, "save", lambda *args, **kwargs: None)
    monkeypatch.setattr(ingestor.database, "save_ingestion_job", lambda *args, **kwargs: None)

    result = ingestor.ingest_records(
        [record(), record()],
        source_name="fixture",
    )
    assert result["processed"] == 2
    assert result["stored"] == 1
    assert result["duplicates"] == 1
    assert result["quality"]["validated_records"] == 2
    assert 0.0 <= result["quality"]["average_confidence"] <= 1.0


def test_ingestion_normalizes_tags_and_rejects_unsafe_rights():
    pipeline = MusicIngestionPipeline()
    normalized = pipeline._normalize(record())
    assert normalized["genres"] == ["hip hop", "soul"]

    with pytest.raises(ValueError, match="dataset_quality"):
        pipeline.ingest(
            record(
                rights={
                    "status": "copyrighted",
                    "sampling_allowed": True,
                    "commercial_use": True,
                }
            )
        )


def test_audio_intelligence_rejects_uncleared_assets(tmp_path):
    audio = tmp_path / "fixture.wav"
    audio.write_bytes(b"placeholder")
    engine = AudioIntelligenceEngine()
    result = engine.index_sample_asset(
        sample_asset_id=1,
        audio_path=str(audio),
        rights_status="copyrighted",
        sampling_allowed=False,
        commercial_use=False,
    )
    assert result["indexed"] is False
    assert result["reason"] == "audio_not_cleared_for_automatic_analysis"


def test_audio_similarity_requires_existing_file(tmp_path):
    engine = AudioIntelligenceEngine()
    with pytest.raises(FileNotFoundError):
        engine.similar_to_audio(str(tmp_path / "missing.wav"))
