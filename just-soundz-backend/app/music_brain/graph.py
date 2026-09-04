from __future__ import annotations

import os
from typing import Any, Dict, List


class MusicGraph:
    """Neo4j adapter for artists, songs, producers, genres and influences."""

    def __init__(self):
        self.uri = os.getenv("JUST_MAKER_NEO4J_URI")
        self.user = os.getenv("JUST_MAKER_NEO4J_USER")
        self.password = os.getenv("JUST_MAKER_NEO4J_PASSWORD")

    @property
    def configured(self) -> bool:
        return bool(self.uri and self.user and self.password)

    def upsert_song_relationships(self, song: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured:
            return {"stored": False, "reason": "neo4j_not_configured"}

        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        query = """
        MERGE (a:Artist {name: $artist})
        MERGE (s:Song {external_id: $external_id})
        SET s.title = $title, s.year = $year
        MERGE (a)-[:PERFORMED]->(s)

        FOREACH (g IN $genres |
            MERGE (genre:Genre {name: g})
            MERGE (s)-[:HAS_GENRE]->(genre)
        )

        FOREACH (p IN $producers |
            MERGE (producer:Producer {name: p})
            MERGE (producer)-[:PRODUCED]->(s)
        )
        """
        with driver:
            with driver.session() as session:
                session.run(
                    query,
                    artist=song["artist_name"],
                    external_id=song["external_id"],
                    title=song["title"],
                    year=song.get("release_year"),
                    genres=song.get("genres", []),
                    producers=song.get("producers", []),
                )
        return {"stored": True}

    def related(self, external_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        if not self.configured:
            return []

        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        query = """
        MATCH (s:Song {external_id: $external_id})
        MATCH (s)-[]-(shared)-[]-(other:Song)
        WHERE other.external_id <> s.external_id
        RETURN other.external_id AS external_id,
               other.title AS title,
               count(shared) AS relationship_score
        ORDER BY relationship_score DESC
        LIMIT $limit
        """
        with driver:
            with driver.session() as session:
                rows = session.run(query, external_id=external_id, limit=limit)
                return [dict(r) for r in rows]
