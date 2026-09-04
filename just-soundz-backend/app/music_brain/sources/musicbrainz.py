from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional

import httpx

from ..provenance import ProvenanceRecord


class MusicBrainzSource:
    """Metadata-only MusicBrainz adapter.

    It intentionally does not download copyrighted recordings. Imported records
    default to reference-only rights until a separate rights source confirms that
    sampling is permitted.
    """

    base_url = "https://musicbrainz.org/ws/2"

    def __init__(self, user_agent: str = "JustMaker/0.6 contact=owner@example.com"):
        self.user_agent = user_agent

    def search_recordings(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        params = {
            "query": query,
            "fmt": "json",
            "limit": min(max(limit, 1), 100),
            "offset": max(offset, 0),
        }
        with httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=30,
        ) as client:
            response = client.get(f"{self.base_url}/recording/", params=params)
            response.raise_for_status()
            return response.json()

    def iter_recordings(
        self,
        query: str,
        max_records: int = 1000,
        page_size: int = 100,
        sleep_seconds: float = 1.05,
    ) -> Iterable[Dict[str, Any]]:
        offset = 0
        yielded = 0
        while yielded < max_records:
            page = self.search_recordings(
                query=query,
                limit=min(page_size, max_records - yielded),
                offset=offset,
            )
            recordings = page.get("recordings") or []
            if not recordings:
                break

            for recording in recordings:
                yield self.normalize(recording)
                yielded += 1
                if yielded >= max_records:
                    break

            offset += len(recordings)
            if len(recordings) < page_size:
                break
            time.sleep(max(sleep_seconds, 1.0))

    def normalize(self, recording: Dict[str, Any]) -> Dict[str, Any]:
        artist_credit = recording.get("artist-credit") or []
        artist_names: List[str] = []
        artist_ids: List[str] = []
        for credit in artist_credit:
            artist = credit.get("artist") or {}
            if artist.get("name"):
                artist_names.append(artist["name"])
            if artist.get("id"):
                artist_ids.append(artist["id"])

        releases = recording.get("releases") or []
        first_release = releases[0] if releases else {}
        release_date = (
            recording.get("first-release-date")
            or first_release.get("date")
            or ""
        )
        release_year: Optional[int] = None
        if len(release_date) >= 4 and release_date[:4].isdigit():
            release_year = int(release_date[:4])

        tags = sorted(
            {
                tag.get("name", "").strip()
                for tag in (recording.get("tags") or [])
                if tag.get("name")
            }
        )

        mbid = str(recording["id"])
        provenance = ProvenanceRecord(
            source_name="musicbrainz",
            source_record_id=mbid,
            source_url=f"https://musicbrainz.org/recording/{mbid}",
            license_name="MusicBrainz metadata terms apply",
            metadata_only=True,
        ).to_dict()

        return {
            "external_id": f"musicbrainz:{mbid}",
            "title": str(recording.get("title") or "Untitled"),
            "artist_name": " & ".join(artist_names) if artist_names else "Unknown Artist",
            "album_name": first_release.get("title"),
            "release_year": release_year,
            "bpm": None,
            "musical_key": None,
            "genres": tags,
            "mood": [],
            "instruments": [],
            "producers": [],
            "metadata": {
                "musicbrainz_recording_id": mbid,
                "musicbrainz_artist_ids": artist_ids,
                "length_ms": recording.get("length"),
                "score": recording.get("score"),
                "provenance": provenance,
            },
            "rights": {
                "status": "reference_only",
                "source": "musicbrainz",
                "commercial_use": False,
                "sampling_allowed": False,
            },
        }
