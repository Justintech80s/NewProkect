class AudioAnalyzer:
    """Essentia-compatible analysis facade with a safe fallback."""

    def analyze(self, audio_path: str):
        try:
            import essentia.standard as es  # optional
            audio = es.MonoLoader(filename=audio_path)()
            rhythm = es.RhythmExtractor2013(method="multifeature")
            bpm, beats, confidence, _, _ = rhythm(audio)
            key, scale, strength = es.KeyExtractor()(audio)
            return {
                "engine": "essentia",
                "bpm": float(bpm),
                "beat_confidence": float(confidence),
                "key": key,
                "scale": scale,
                "key_strength": float(strength),
            }
        except Exception as exc:
            return {
                "engine": "fallback",
                "bpm": None,
                "key": None,
                "message": f"Essentia unavailable or analysis failed: {exc.__class__.__name__}",
            }
