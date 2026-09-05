from __future__ import annotations

from typing import Any, Dict

from .database import MusicDatabase


class ProductionProfileStore:
    """Derives and persists searchable production traits for catalog records."""

    def __init__(self, db: MusicDatabase | None = None):
        self.db = db or MusicDatabase()

    def infer(self, song: Dict[str, Any]) -> Dict[str, Any]:
        bpm = song.get("bpm")
        year = song.get("release_year")
        genres = {str(x).lower() for x in (song.get("genres") or [])}
        mood = {str(x).lower() for x in (song.get("mood") or [])}

        era = f"{(int(year)//10)*10}s" if year else None
        if bpm is None:
            tempo_bucket = None
        elif float(bpm) < 80:
            tempo_bucket = "slow"
        elif float(bpm) < 105:
            tempo_bucket = "midtempo"
        elif float(bpm) < 135:
            tempo_bucket = "uptempo"
        else:
            tempo_bucket = "fast"

        techniques = list(song.get("techniques") or [])
        texture_tags = list(song.get("texture_tags") or [])

        sample_chop = 0.72 if {"boom bap", "hip hop", "soul"} & genres else 0.35
        harmonic = 0.62 if {"soul", "jazz", "r&b"} & genres else 0.42
        bass = 0.78 if {"hip hop", "funk", "trap"} & genres else 0.58
        energy = 0.78 if {"aggressive", "energetic"} & mood else 0.52

        return {
            "era": era,
            "tempo_bucket": tempo_bucket,
            "energy": energy,
            "swing": None,
            "syncopation": None,
            "drum_density": None,
            "harmonic_complexity": harmonic,
            "bass_prominence": bass,
            "sample_chop_intensity": sample_chop,
            "texture_tags": texture_tags,
            "techniques": techniques,
            "metadata": {"inference": "phase25-rules-v1"},
        }

    def save(self, song_id: int, profile: Dict[str, Any]) -> None:
        if not self.db.configured:
            return

        import json
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO production_profiles(
                        song_id,era,tempo_bucket,energy,swing,syncopation,
                        drum_density,harmonic_complexity,bass_prominence,
                        sample_chop_intensity,texture_tags,techniques,metadata
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (song_id)
                    DO UPDATE SET
                        era=EXCLUDED.era,
                        tempo_bucket=EXCLUDED.tempo_bucket,
                        energy=EXCLUDED.energy,
                        swing=EXCLUDED.swing,
                        syncopation=EXCLUDED.syncopation,
                        drum_density=EXCLUDED.drum_density,
                        harmonic_complexity=EXCLUDED.harmonic_complexity,
                        bass_prominence=EXCLUDED.bass_prominence,
                        sample_chop_intensity=EXCLUDED.sample_chop_intensity,
                        texture_tags=EXCLUDED.texture_tags,
                        techniques=EXCLUDED.techniques,
                        metadata=EXCLUDED.metadata,
                        updated_at=NOW()
                    """,
                    (
                        song_id,
                        profile.get("era"),
                        profile.get("tempo_bucket"),
                        profile.get("energy"),
                        profile.get("swing"),
                        profile.get("syncopation"),
                        profile.get("drum_density"),
                        profile.get("harmonic_complexity"),
                        profile.get("bass_prominence"),
                        profile.get("sample_chop_intensity"),
                        profile.get("texture_tags", []),
                        profile.get("techniques", []),
                        json.dumps(profile.get("metadata", {})),
                    ),
                )
                conn.commit()
