from __future__ import annotations

from typing import Any, Dict, Iterable

from .database import MusicDatabase
from .embeddings import MusicEmbeddingEngine
from .graph import MusicGraph
from .rights import SampleRightsEngine


class MusicIngestionPipeline:
    """Normalizes and stores song metadata, embeddings, graph links and rights."""

    def __init__(self):
        self.db = MusicDatabase()
        self.graph = MusicGraph()
        self.embeddings = MusicEmbeddingEngine()
        self.rights = SampleRightsEngine()

    def ingest(self, record: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize(record)
        db_result = self.db.upsert_song(normalized)

        rights = normalized.get("rights") or {"status": "unknown"}
        rights_eval = self.rights.evaluate(rights)

        if db_result.get("stored"):
            song_id = int(db_result["id"])
            self.db.set_rights(song_id, rights)

            semantic_text = self._semantic_text(normalized)
            embedding = self.embeddings.text_embedding(semantic_text)
            self.db.set_embedding(song_id, embedding)

            provenance = (
                normalized.get("metadata", {}).get("provenance")
                if isinstance(normalized.get("metadata"), dict)
                else None
            )
            if provenance:
                self.db.set_provenance(song_id, provenance)

        graph_result = self.graph.upsert_song_relationships(normalized)

        return {
            "record": normalized,
            "database": db_result,
            "graph": graph_result,
            "rights": rights_eval,
        }

    def _normalize(self, r: Dict[str, Any]) -> Dict[str, Any]:
        required = ["external_id", "title", "artist_name"]
        missing = [k for k in required if not r.get(k)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        return {
            "external_id": str(r["external_id"]),
            "title": str(r["title"]).strip(),
            "artist_name": str(r["artist_name"]).strip(),
            "album_name": r.get("album_name"),
            "release_year": r.get("release_year"),
            "bpm": r.get("bpm"),
            "musical_key": r.get("musical_key"),
            "genres": list(r.get("genres") or []),
            "mood": list(r.get("mood") or []),
            "instruments": list(r.get("instruments") or []),
            "producers": list(r.get("producers") or []),
            "metadata": dict(r.get("metadata") or {}),
            "rights": dict(r.get("rights") or {"status": "unknown"}),
        }

    def _semantic_text(self, r: Dict[str, Any]) -> str:
        parts: Iterable[str] = [
            r["title"],
            r["artist_name"],
            r.get("album_name") or "",
            " ".join(r.get("genres") or []),
            " ".join(r.get("mood") or []),
            " ".join(r.get("instruments") or []),
            " ".join(r.get("producers") or []),
            str(r.get("release_year") or ""),
            str(r.get("bpm") or ""),
            str(r.get("musical_key") or ""),
        ]
        return " | ".join(x for x in parts if x)
