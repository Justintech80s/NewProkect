from app.services.candidate_budget import CandidateBudgetPlanner


def test_manual_mode_preserves_requested_count():
    result = CandidateBudgetPlanner().decide(
        requested_count=3,
        quality_threshold=0.72,
        duration_seconds=120,
        make_stems=False,
        prompt="simple beat",
        mode="manual",
    )
    assert result["candidate_count"] == 3


def test_adaptive_mode_spends_more_on_difficult_high_quality_request():
    result = CandidateBudgetPlanner().decide(
        requested_count=3,
        quality_threshold=0.9,
        duration_seconds=300,
        make_stems=False,
        prompt="evolving cinematic orchestral soundtrack",
        mode="adaptive",
    )
    assert result["candidate_count"] == 3


def test_adaptive_mode_saves_compute_on_simple_request():
    result = CandidateBudgetPlanner().decide(
        requested_count=3,
        quality_threshold=0.72,
        duration_seconds=90,
        make_stems=False,
        prompt="simple drum beat",
        mode="adaptive",
    )
    assert result["candidate_count"] == 1


def test_adaptive_mode_never_exceeds_requested_max():
    result = CandidateBudgetPlanner().decide(
        requested_count=2,
        quality_threshold=0.95,
        duration_seconds=500,
        make_stems=False,
        prompt="complex evolving cinematic soundtrack",
        mode="adaptive",
    )
    assert result["candidate_count"] == 2
