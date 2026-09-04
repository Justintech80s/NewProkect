from app.music_brain.context import MusicBrainContextBuilder


class FakeSearch:
    def search(self, query, limit=20, sample_eligible_only=False):
        if sample_eligible_only:
            rows = [{
                "id": 9,
                "title": "Cleared Loop",
                "artist": "Library",
                "year": 1974,
                "bpm": 94,
                "key": "F# minor",
                "genres": ["soul"],
                "mood": ["dark"],
                "instruments": ["strings"],
                "rights_status": "licensed",
                "sampling_allowed": True,
                "similarity": 0.91,
            }]
        else:
            rows = [
                {
                    "id": 1, "title": "A", "artist": "Artist A", "year": 1972,
                    "bpm": 92, "key": "F# minor", "genres": ["soul", "funk"],
                    "mood": ["dark"], "instruments": ["strings", "rhodes"],
                    "rights_status": "reference_only", "sampling_allowed": False,
                    "similarity": 0.9,
                },
                {
                    "id": 2, "title": "B", "artist": "Artist B", "year": 1976,
                    "bpm": 96, "key": "F# minor", "genres": ["soul"],
                    "mood": ["dark"], "instruments": ["strings"],
                    "rights_status": "reference_only", "sampling_allowed": False,
                    "similarity": 0.88,
                },
            ]
        return {
            "results": rows,
            "database_configured": True,
            "graph_configured": False,
        }


def test_context_guides_plan_without_overriding_user_values():
    builder = MusicBrainContextBuilder(FakeSearch())
    context = builder.build("dark 70s soul")
    plan = {
        "bpm": 100,
        "key": "C minor",
        "arrangement": [],
    }

    enriched = builder.apply_to_plan(
        plan,
        context,
        user_bpm_supplied=False,
        user_key_supplied=False,
    )

    assert enriched["bpm"] == 94
    assert enriched["key"] == "F# minor"
    assert enriched["music_brain"]["reference_count"] == 2
    assert enriched["music_brain"]["eligible_sample_count"] == 1
    assert "soul" in enriched["production_context"]["genres"]


def test_explicit_bpm_and_key_are_preserved():
    builder = MusicBrainContextBuilder(FakeSearch())
    context = builder.build("dark 70s soul")
    plan = {"bpm": 110, "key": "D minor", "arrangement": []}

    enriched = builder.apply_to_plan(
        plan,
        context,
        user_bpm_supplied=True,
        user_key_supplied=True,
    )

    assert enriched["bpm"] == 110
    assert enriched["key"] == "D minor"
