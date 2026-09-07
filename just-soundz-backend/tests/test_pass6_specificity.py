from app.services.producer import ProducerPlanner
from app.services.conditioning import ConditioningCompiler
from app.services.instrumentation_planner import InstrumentationPlanner


PROMPT = "Create a 90s sounding hip hop beat east coast sample chops live drums and live bass"


def test_specific_prompt_becomes_explicit_production_intent():
    plan = ProducerPlanner().build_plan(PROMPT, bpm=None, key=None, duration_seconds=120)

    assert plan["bpm"] == 92
    assert plan["style_intent"]["era"] == "1990s"
    assert plan["style_intent"]["region"] == "east-coast-us"
    assert plan["style_intent"]["groove_family"] == "boom-bap"
    assert plan["performance"]["live_drums"] is True
    assert plan["performance"]["live_bass"] is True
    assert plan["sampling"]["requested"] is True
    assert plan["sampling"]["avoid_loop_only_behavior"] is True
    assert plan["bass"]["type"] == "live electric bass"
    assert "avoid modern trap hi-hat rolls unless explicitly requested" in plan["negative_instructions"]


def test_explicit_instruments_are_prioritized():
    plan = ProducerPlanner().build_plan(PROMPT, bpm=None, key=None, duration_seconds=120)
    plan["producer_dna"] = {"archetype": "gritty_cinematic_sampler"}
    instrumented = InstrumentationPlanner().apply(plan)

    primary = instrumented["instrumentation_plan"]["primary"]
    assert primary[0] == "human-played acoustic drum kit"
    assert primary[1] == "live electric bass guitar"
    assert "chopped cleared sample texture" in primary


def test_conditioning_preserves_non_generic_intent():
    plan = ProducerPlanner().build_plan(PROMPT, bpm=None, key=None, duration_seconds=120)
    plan["producer_dna"] = {}
    plan = InstrumentationPlanner().apply(plan)
    conditioned = ConditioningCompiler().compile(plan)

    assert conditioned["style_intent"]["era"] == "1990s"
    assert conditioned["performance"]["live_drums"] is True
    assert conditioned["performance"]["live_bass"] is True
    assert conditioned["sampling_intent"]["requested"] is True
    assert conditioned["instrumentation"]["explicit_user_instruments"]
