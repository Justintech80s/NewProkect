from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .embeddings import MusicEmbeddingEngine
from .database import MusicDatabase
from ..services.reference_audio import ReferenceAudioAnalyzer


ALLOWED_AUDIO_EMBEDDING_RIGHTS = {
    "public_domain",
    "royalty_free",
    "licensed",
    "partner_cleared",
    "user_owned",
    "creative_commons_sampling_allowed",
}


class AudioIntelligenceEngine:
    """Builds sonic embeddings/traits only for audio that is cleared for analysis."""

    def __init__(self):
        self.embeddings = MusicEmbeddingEngine()
        self.database = MusicDatabase()
        self.analyzer = ReferenceAudioAnalyzer()

    def index_sample_asset(
        self,
        *,
        sample_asset_id: int,
        audio_path: str,
        rights_status: str,
        sampling_allowed: bool,
        commercial_use: bool,
    ) -> Dict[str, Any]:
        status = str(rights_status or "unknown").strip().lower()
        eligible = (
            status in ALLOWED_AUDIO_EMBEDDING_RIGHTS
            and bool(sampling_allowed)
            and (bool(commercial_use) or status == "user_owned")
        )
        if not eligible:
            return {
                "indexed": False,
                "reason": "audio_not_cleared_for_automatic_analysis",
                "rights_status": status,
            }

        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(str(path))

        embedding = self.embeddings.audio_embedding(str(path))
        analysis = self.analyzer.analyze(str(path))
        traits = analysis.get("production_traits") or {}

        stored = self.database.set_sample_audio_embedding(
            sample_asset_id,
            embedding,
            traits=traits,
            metadata={
                "sample_rate": analysis.get("sample_rate"),
                "duration_seconds": analysis.get("duration_seconds"),
                "spectral_centroid_hz": analysis.get("spectral_centroid_hz"),
                "band_energy": analysis.get("band_energy"),
            },
        )
        return {
            "indexed": bool(stored),
            "sample_asset_id": sample_asset_id,
            "rights_status": status,
            "embedding_dimension": len(embedding),
            "production_traits": traits,
        }

    def similar_to_audio(
        self,
        audio_path: str,
        *,
        limit: int = 20,
    ) -> Dict[str, Any]:
        embedding = self.embeddings.audio_embedding(audio_path)
        return {
            "query_type": "audio",
            "results": self.database.audio_sample_similarity_search(
                embedding,
                limit=limit,
            ),
        }
