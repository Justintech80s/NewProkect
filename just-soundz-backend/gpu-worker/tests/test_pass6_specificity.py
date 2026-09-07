from prompt_compiler import ConditioningPromptCompiler


def test_compiler_turns_structured_intent_into_audible_instructions():
    plan = {
        "original_prompt": "90s east coast hip hop with sample chops, live drums and live bass",
        "bpm": 92,
        "key": "C minor",
        "novelty": {"concept": "rhythmic pocket contrast"},
    }
    conditioning = {
        "text": {"prompt": plan["original_prompt"], "negative": []},
        "style_intent": {
            "era": "1990s",
            "region": "east-coast-us",
            "groove_family": "boom-bap",
        },
        "performance": {
            "live_drums": True,
            "live_bass": True,
            "humanization_required": True,
        },
        "sampling_intent": {
            "requested": True,
            "avoid_loop_only_behavior": True,
        },
        "musical": {
            "bpm": 92,
            "key": "C minor",
            "harmony": {"progression": ["i", "VI", "III", "VII"]},
        },
        "production": {
            "swing": 0.60,
            "syncopation": 0.65,
            "negative_space": 0.60,
            "sample_chop_intensity": 0.80,
        },
        "instrumentation": {
            "primary": ["human-played acoustic drum kit", "live electric bass guitar"],
            "explicit_user_instruments": ["human-played acoustic drum kit", "live electric bass guitar"],
        },
        "rhythm": {"swing": 0.60, "percussion": [3, 11]},
        "arrangement": [
            {"section": "intro", "bars": 4},
            {"section": "verse", "bars": 16},
            {"section": "hook", "bars": 8},
        ],
        "advanced_controls": {
            "sections": [{"section": "verse", "energy": 0.58}],
            "rhythm": {"kick": [{"step": 0}], "snare": [{"step": 4}]},
        },
        "reference": {},
        "novelty": {"concept": "rhythmic pocket contrast"},
    }

    compiled = ConditioningPromptCompiler().compile(plan, conditioning, variation=1)

    required = [
        "1990s production language",
        "east coast us",
        "boom bap",
        "human-played acoustic drum kit feel",
        "live electric bass guitar feel",
        "sample-chop behavior",
        "do not leave the source as a static repeated loop",
        "each section must audibly differ",
        "generic preset-demo arrangement",
        "unchanged four-bar looping",
        "mechanically quantized live-instrument feel",
    ]
    for phrase in required:
        assert phrase in compiled


def test_compiler_does_not_request_uncleared_sampling():
    conditioning = {
        "text": {"prompt": "sample chops"},
        "sampling_intent": {"requested": True, "avoid_loop_only_behavior": True},
        "musical": {},
        "production": {},
        "instrumentation": {},
        "rhythm": {},
        "arrangement": [],
        "advanced_controls": {},
        "reference": {},
        "style_intent": {},
        "performance": {},
        "novelty": {},
    }
    compiled = ConditioningPromptCompiler().compile({}, conditioning, variation=0)
    assert "only cleared, licensed or user-owned source material" in compiled
