# Pass 3 DSP / Mastering / Stems Verification

Repository/code-complete scope for the Just Maker five-subsystem hardening plan.

| Criterion | Implementation | Test / CI evidence | Status |
|---|---|---|---|
| Rust DSP and NumPy fallback produce compatible bounded outputs | app/services/rust_dsp.py; rust-dsp/src/lib.rs | tests/test_audio_pass3.py::test_rust_and_numpy_dsp_paths_are_compatible; Rust unit tests | PASS |
| Mastering validates sample format, channels, duration, finite values, peak bounds, output existence | app/services/audio_safety.py; app/services/mastering.py | silence, clipped, malformed, empty, non-finite, short-audio tests | PASS |
| Stem mixer validates requested stems and reports missing/invalid conditions | app/services/stem_mixer.py | missing-stem, invalid-stem, sample-rate-mismatch tests | PASS |
| Gain staging prevents clipping before and after mixdown | app/services/stem_mixer.py | multi-stem bounded-output test | PASS |
| Mastering critic thresholds and correction passes are deterministic and capped | app/services/mastering_critic.py; app/main.py | test_mastering_critic_correction_cap_is_deterministic | PASS |
| DSP failures cannot overwrite/delete original render | app/services/mastering.py | test_dsp_failure_never_overwrites_original | PASS |
| Master and stems carry structured technical metadata | app/services/mastering.py; app/services/stem_mixer.py; app/main.py | mastering and multi-stem metadata assertions | PASS |
| Tests cover silence, clipped audio, DC offset, short files, malformed files, missing stems, multi-stem mixes | tests/test_audio_pass3.py | dedicated audio contract CI | PASS |
| Rust CI and Python audio tests both run | .github/workflows/just-maker-rust-dsp-ci.yml; .github/workflows/just-maker-backend-ci.yml | cargo test + pytest test_audio_pass3.py | PASS |

External GPU generation remains outside repository/code-complete scope. The audio-processing contracts are deterministic and testable without external services.
