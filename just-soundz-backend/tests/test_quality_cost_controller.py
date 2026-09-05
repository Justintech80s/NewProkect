from app.services.quality_cost_controller import QualityCostController


class FakeOperations:
    def estimate_generation_cost(self, duration_seconds, attempts=1, stem_count=1):
        return duration_seconds * attempts * stem_count * 0.001


def test_no_budget_keeps_candidate_count():
    controller = QualityCostController(FakeOperations())
    result = controller.plan(
        duration_seconds=100,
        candidate_count=3,
        make_stems=False,
        max_estimated_cost_usd=None,
    )
    assert result["candidate_count"] == 3
    assert result["budget_limited"] is False


def test_budget_reduces_candidate_fanout():
    controller = QualityCostController(FakeOperations())
    result = controller.plan(
        duration_seconds=100,
        candidate_count=3,
        make_stems=False,
        max_estimated_cost_usd=0.21,
    )
    assert result["candidate_count"] == 2
    assert result["budget_limited"] is True


def test_stems_are_accounted_as_more_expensive():
    controller = QualityCostController(FakeOperations())
    plain = controller.plan(
        duration_seconds=100,
        candidate_count=1,
        make_stems=False,
        max_estimated_cost_usd=None,
    )
    stems = controller.plan(
        duration_seconds=100,
        candidate_count=1,
        make_stems=True,
        max_estimated_cost_usd=None,
    )
    assert stems["estimated_cost_usd"] > plain["estimated_cost_usd"]
