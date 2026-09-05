from __future__ import annotations

from typing import Any, Dict, List

from .database import MusicDatabase
from .embeddings import MusicEmbeddingEngine
from .graph import MusicGraph
from .relational_graph import RelationalMusicGraph
from ..services.local_cache import RocksLocalCache
from ..services.cache_tuner import AdaptiveCacheTuner


class MusicBrainSearch:
    """Combines vector similarity with relationship-graph expansion."""

    def __init__(self):
        self.db = MusicDatabase()
        self.embeddings = MusicEmbeddingEngine()
        self.graph = MusicGraph()
        self.relational_graph = RelationalMusicGraph(self.db)
        self.cache = RocksLocalCache("music-brain-search")
        self.cache_tuner = AdaptiveCacheTuner()

    def search(
        self,
        query: str,
        limit: int = 20,
        sample_eligible_only: bool = False,
    ) -> Dict[str, Any]:
        cache_key = self.cache.make_key(
            "search",
            {
                "query": query,
                "limit": limit,
                "sample_eligible_only": sample_eligible_only,
            },
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            return {
                **cached,
                "cache": {
                    "hit": True,
                    **self.cache.status(),
                },
            }

        embedding = self.embeddings.text_embedding(query)
        if sample_eligible_only:
            vector_results = self.db.semantic_sample_search(
                embedding,
                limit=limit,
            )
        else:
            vector_results = self.db.semantic_search_with_profiles(
                embedding,
                limit=limit,
            )

        graph_results = []
        relational_graph_results = []
        if vector_results:
            top_song_id = vector_results[0].get("id")
            if top_song_id:
                relational_graph_results = self.relational_graph.related_songs(
                    int(top_song_id),
                    limit=min(limit, 25),
                )

        if self.graph.configured and vector_results:
            top_external_id = vector_results[0].get("external_id")
            if top_external_id:
                graph_results = self.graph.related(top_external_id, limit=min(limit, 25))

        result = {
            "query": query,
            "sample_eligible_only": sample_eligible_only,
            "results": vector_results,
            "graph_results": graph_results,
            "relational_graph_results": relational_graph_results,
            "database_configured": self.db.configured,
            "graph_configured": self.graph.configured,
            "cache": {
                "hit": False,
                **self.cache.status(),
            },
        }
        ttl = self.cache_tuner.ttl_for(self.cache)
        self.cache.set(cache_key, result, ttl_seconds=ttl)
        result["cache"]["ttl_seconds"] = ttl
        result["cache"]["tuning"] = self.cache_tuner.recommend(
            self.cache.metrics(),
            namespace=self.cache.namespace,
            base_ttl=self.cache.default_ttl,
        )
        return result
