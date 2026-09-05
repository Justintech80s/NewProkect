from pathlib import Path
import wave

from app.services.arranger import ArrangementEngine
from app.services.mastering import MasteringEngine
from app.services.procedural import ProceduralMusicProvider
from app.services.repetition import RepetitionDetector
from app.services.section_repair import SectionRepairEngine


def test_arranger_enriches_sections():
    engine = ArrangementEngine()
    plan = {
        "arrangement": [
            {"section": "intro", "bars": 8},
            {"section": "hook", "bars": 8},
        ]
    }
    out = engine.apply(plan)
    assert out["arrangement"][0]["energy"] < out["arrangement"][1]["energy"]


def test_mastering_and_repetition_pipeline():
    provider = ProceduralMusicProvider()
    generated = provider.generate({
        "bpm": 96,
        "key": "C minor",
        "duration_seconds": 10,
        "drums": {"density": "medium"},
        "arrangement": [],
    })

    detector = RepetitionDetector()
    repetition = detector.inspect(generated["audio_path"])
    assert "score" in repetition

    mastering = MasteringEngine()
    result = mastering.process(generated["audio_path"])
    assert result["mastered"] is True
    path = Path(result["audio_path"])
    assert path.exists()

    with wave.open(str(path), "rb") as wf:
        assert wf.getnframes() > 0


def test_section_repair_changes_plan():
    repair = SectionRepairEngine()
    plan = {
        "arrangement": [
            {"section": "verse", "bars": 16, "energy": 0.55},
            {"section": "hook", "bars": 8, "energy": 0.95},
        ],
        "drums": {"density": "medium"},
    }
    fixed = repair.repair_plan(plan, {"score": 0.95}, attempt=1)
    assert fixed["arrangement"] != plan["arrangement"]


def test_mastering_fade_handles_mono_channel_matrix():
    provider = ProceduralMusicProvider()
    generated = provider.generate({
        "bpm": 90,
        "key": "C minor",
        "duration_seconds": 10,
        "drums": {"density": "medium"},
        "arrangement": [],
    })

    result = MasteringEngine().process(generated["audio_path"])

    assert result["mastered"] is True
    assert result["peak_dbfs"] <= -0.3
