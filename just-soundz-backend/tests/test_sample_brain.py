from app.services.sample_brain import SampleBrain


def test_sample_brain_never_selects_reference_only_audio():
    brain = SampleBrain()
    plan = {
        "bpm": 94,
        "key": "F# minor",
        "music_brain": {
            "eligible_samples": [
                {
                    "id": 1, "title": "Reference", "sampling_allowed": False,
                    "similarity": 0.99, "bpm": 94, "key": "F# minor",
                },
                {
                    "id": 2, "title": "Cleared", "sampling_allowed": True,
                    "similarity": 0.80, "bpm": 92, "key": "F# minor",
                },
            ]
        },
    }
    result = brain.prepare(plan)
    assert result["eligible_count"] == 1
    assert result["selected"][0]["title"] == "Cleared"


def test_sample_brain_builds_tempo_transform():
    brain = SampleBrain()
    plan = {
        "bpm": 100,
        "key": "C minor",
        "music_brain": {
            "eligible_samples": [{
                "id": 2, "title": "Loop", "sampling_allowed": True,
                "similarity": 0.8, "bpm": 80, "key": "A minor",
            }]
        },
    }
    result = brain.prepare(plan)
    assert result["selected"][0]["transform"]["time_stretch_ratio"] == 1.25
