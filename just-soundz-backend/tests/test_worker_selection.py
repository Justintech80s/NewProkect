from app.services.capabilities import WorkerCapabilities
from app.services.model_registry import WorkerConfig
from app.services.worker_selector import WorkerSelector


class FakeRegistry:
    def workers(self):
        return [
            WorkerConfig(
                name="limited",
                kind="stable-audio-worker",
                url="https://limited.example",
                token=None,
                priority=10,
                capabilities=WorkerCapabilities(
                    text_prompt=True,
                    bpm=False,
                    key=False,
                    rhythm_conditioning=False,
                    harmony_conditioning=False,
                    instrumentation_conditioning=True,
                    arrangement_conditioning=False,
                    max_duration_seconds=180,
                ),
            ),
            WorkerConfig(
                name="full",
                kind="http-worker",
                url="https://full.example",
                token=None,
                priority=20,
                capabilities=WorkerCapabilities(
                    text_prompt=True,
                    bpm=True,
                    key=True,
                    rhythm_conditioning=True,
                    harmony_conditioning=True,
                    instrumentation_conditioning=True,
                    arrangement_conditioning=True,
                    stem_conditioning=True,
                    sample_conditioning=True,
                    negative_prompt=True,
                    max_duration_seconds=600,
                ),
            ),
        ]


def test_selector_prefers_full_conditioning_worker():
    selector = WorkerSelector(FakeRegistry())
    plan = {
        "duration_seconds": 120,
        "conditioning": {
            "text": {"prompt": "x", "negative": ["avoid clipping"]},
            "musical": {"bpm": 94, "key": "C minor", "harmony": {"progression": ["i"]}},
            "rhythm": {"grid": "16-step"},
            "instrumentation": {"primary": ["bass"]},
            "arrangement": [{"section": "verse"}],
            "stems": {"stems": {"drums": {}}},
            "samples": {"processed": [{"audio_path": "/tmp/x.wav"}]},
        },
    }

    ranked = selector.rank(plan)
    assert ranked[0][0].name == "full"
    assert ranked[0][1]["coverage"] == 1.0
