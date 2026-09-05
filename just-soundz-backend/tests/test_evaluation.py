from app.services.evaluation import GenerationEvaluator


def test_evaluator_scores_aligned_generation():
    evaluator = GenerationEvaluator()
    result = evaluator.evaluate(
        plan={
            "bpm": 94,
            "key": "C minor",
            "conditioning": {
                "text": {"prompt": "x"},
                "musical": {"bpm": 94},
                "rhythm": {"grid": "16-step"},
                "production": {"archetype": "modern_minimal"},
                "instrumentation": {"primary": ["bass"]},
                "arrangement": [{"section": "verse"}],
                "advanced_controls": {"tempo": {"bpm": 94}},
            },
        },
        generation={"provider": "gpu:test", "routing": {"attempts": []}},
        analysis={"bpm": 94, "key": "C"},
        quality={"score": 0.9, "prompt_match": 0.9},
        repetition={"score": 0.65, "too_repetitive": False},
        mastering={"mastered": True, "critic": {"score": 1.0}},
        stems={"enabled": True, "generated": [{"stem": str(i)} for i in range(6)]},
        artifacts=[{"sha256": "a"*64, "size_bytes": 1000}],
    )
    assert result["pass"] is True
    assert result["grade"] in {"A", "B", "C"}
