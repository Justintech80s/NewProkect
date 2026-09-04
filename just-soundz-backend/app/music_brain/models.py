from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RightsInfo:
    status: str
    source: Optional[str] = None
    license_name: Optional[str] = None
    commercial_use: bool = False
    sampling_allowed: bool = False


@dataclass
class SongRecord:
    id: str
    title: str
    artist: str
    album: Optional[str] = None
    year: Optional[int] = None
    genres: List[str] = field(default_factory=list)
    producers: List[str] = field(default_factory=list)
    bpm: Optional[float] = None
    musical_key: Optional[str] = None
    mood: List[str] = field(default_factory=list)
    instruments: List[str] = field(default_factory=list)
    rights: Optional[RightsInfo] = None
