from app.services.candidate_ranker import CandidateRanker


def test_ranker_prefers_passing_higher_quality_candidate():
    ranker = CandidateRanker()
    candidates = [
        {
            "variation": 0,
            "evaluation": {"score": 0.72, "grade": "D", "pass": False},
            "production_critic": {"pass": True},
            "mastering": {"critic": {"pass": True}},
            "repetition": {"too_repetitive": False},
        },
        {
            "variation": 1,
            "evaluation": {"score": 0.84, "grade": "B", "pass": True},
            "production_critic": {"pass": True},
            "mastering": {"critic": {"pass": True}},
            "repetition": {"too_repetitive": False},
        },
    ]
    ranked = ranker.rank(candidates)
    assert ranked[0]["variation"] == 1


def test_ranker_penalizes_repetition():
    ranker = CandidateRanker()
    candidates = [
        {
            "variation": 0,
            "evaluation": {"score": 0.82, "grade": "B", "pass": True},
            "production_critic": {"pass": False},
            "mastering": {"critic": {"pass": False}},
            "repetition": {"too_repetitive": True},
        },
        {
            "variation": 1,
            "evaluation": {"score": 0.80, "grade": "C", "pass": True},
            "production_critic": {"pass": True},
            "mastering": {"critic": {"pass": True}},
            "repetition": {"too_repetitive": False},
        },
    ]
    assert ranker.rank(candidates)[0]["variation"] == 1
