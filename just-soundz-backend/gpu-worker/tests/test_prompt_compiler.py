from prompt_compiler import ConditioningPromptCompiler


def test_compiler_contains_core_music_controls():
    compiler = ConditioningPromptCompiler()
    prompt = compiler.compile(
        {
            "original_prompt": "dark cinematic hip hop instrumental",
            "bpm": 92,
            "key": "C minor",
        },
        {
            "text": {"prompt": "dark cinematic hip hop instrumental"},
            "musical": {
                "bpm": 92,
                "key": "C minor",
                "harmony": {"progression": ["i", "VI", "III", "VII"]},
            },
            "production": {
                "archetype": "gritty_cinematic_sampler",
                "swing": 0.57,
                "syncopation": 0.63,
            },
            "instrumentation": {
                "primary": ["dusty drums", "dark piano", "low strings"],
            },
            "rhythm": {"swing": 0.57, "percussion": [3, 11]},
            "arrangement": [{"section": "verse", "bars": 16}],
        },
        1,
    )

    assert "92 BPM" in prompt
    assert "C minor" in prompt
    assert "gritty cinematic sampler" in prompt
    assert "original instrumental composition" in prompt
