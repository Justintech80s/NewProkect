class QualityJudge:
    """CLAP-compatible text/audio quality gate with a deterministic fallback."""

    def score(self, prompt: str, audio_path: str, analysis: dict):
        try:
            # Adapter point for LAION-CLAP or a hosted audio-text embedding service.
            # We do not hard-code noncommercial model weights here.
            import laion_clap  # noqa: F401
            return {
                "engine": "clap-adapter",
                "score": 0.80,
                "prompt_match": 0.80,
                "note": "CLAP package detected; replace placeholder with production embedding call.",
            }
        except Exception:
            base = 0.55
            if analysis.get("bpm"):
                base += 0.10
            if analysis.get("key"):
                base += 0.10
            return {
                "engine": "fallback",
                "score": min(base, 0.75),
                "prompt_match": None,
                "note": "Install/configure an approved CLAP service for semantic audio-text scoring.",
            }
