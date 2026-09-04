from app.services.stem_generator import ProfessionalStemGenerator


def test_stem_generator_builds_separate_requests():
    plan = {
        "stem_arrangement": {
            "stems": {
                "drums": {"gain_db": -5},
                "bass": {"gain_db": -6},
                "harmony": {"gain_db": -10},
            },
            "sections": [],
        },
        "instrumentation_plan": {
            "primary": ["dusty drums", "sub bass", "dark piano"],
            "secondary": ["ambient texture"],
        },
        "negative_instructions": [],
    }

    requests = ProfessionalStemGenerator().build_requests(plan)
    stems = [x["stem"] for x in requests]

    assert stems == ["drums", "bass", "harmony"]
    assert requests[0]["plan"]["stem_target"] == "drums"
    assert "no bass line" in requests[0]["plan"]["negative_instructions"]
