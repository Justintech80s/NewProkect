from app.services.mastering_critic import MasteringCritic
from app.services.mix_intelligence import MixIntelligence


def test_mix_intelligence_applies_gain_and_eq_corrections():
    engine = MixIntelligence()
    arrangement = {
        "stems": {
            "drums": {"gain_db": -5.0},
            "bass": {"gain_db": -6.0},
        }
    }
    analysis = {
        "stems": [
            {
                "stem": "drums",
                "recommended_gain_db": -2.0,
                "mud_risk": True,
                "harshness_risk": False,
                "clipping_risk": True,
            }
        ],
        "issues": ["stem_clipping_risk"],
    }

    adjusted = engine.apply_bus_corrections(arrangement, analysis)

    assert adjusted["stems"]["drums"]["gain_db"] == -7.0
    assert adjusted["stems"]["drums"]["eq"]["mud_cut_db"] < 0
    assert adjusted["stems"]["drums"]["limiter"]["enabled"] is True


def test_mastering_critic_flags_hot_master():
    result = MasteringCritic().evaluate({
        "mastered": True,
        "peak_dbfs": -0.1,
        "rms_dbfs": -10.0,
        "crest_factor": 2.2,
    })
    assert result["pass"] is False
    assert "peak_too_hot" in result["issues"]
