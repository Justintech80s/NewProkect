from app.services.producer import ProducerPlanner


def test_prompt_to_plan_extracts_bpm_and_instrumental():
    planner = ProducerPlanner()
    plan = planner.build_plan(
        "dark 102 BPM instrumental with sparse drums",
        bpm=None,
        key=None,
        duration_seconds=120,
    )
    assert plan["bpm"] == 102
    assert plan["vocals"] == "none"
    assert plan["drums"]["density"] == "sparse"
