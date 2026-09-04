from __future__ import annotations

from typing import Any, Dict, List

from .database import MusicDatabase
from .embeddings import MusicEmbeddingEngine
from .graph import MusicGraph


class MusicBrainSearch:
    """Combines vector similarity with relationship-graph expansion."""

    def __init__(self):
        self.db = MusicDatabase()
        self.embeddings = MusicEmbeddingEngine()
        self.graph = MusicGraph()

    def search(
        self,
        query: str,
        limit: int = 20,
        sample_eligible_only: bool = False,
    ) -> Dict[str, Any]:
        embedding = self.embeddings.text_embedding(query)
        vector_results = self.db.semantic_search(
            embedding,
            limit=limit,
            only_sample_eligible=sample_eligible_only,
        )

        graph_results = []
        if self.graph.configured and vector_results:
            top_external_id = vector_results[0].get("external_id")
            if top_external_id:
                graph_results = self.graph.related(top_external_id, limit=min(limit, 25))

        return {
            "query": query,
            "sample_eligible_only": sample_eligible_only,
            "results": vector_results,
            "graph_results": graph_results,
            "database_configured": self.db.configured,
            "graph_configured": self.graph.configured,
        }
