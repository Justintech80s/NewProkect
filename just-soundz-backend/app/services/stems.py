import os
import subprocess
from pathlib import Path

class StemSeparator:
    """Demucs-compatible stem service. Disabled unless explicitly enabled."""

    def separate(self, audio_path: str):
        if os.getenv("JUST_SOUNDZ_ENABLE_DEMUCS", "0") != "1":
            return {"enabled": False, "engine": "demucs", "reason": "not configured"}

        out_dir = Path(os.getenv("JUST_SOUNDZ_STEM_DIR", "/tmp/just-soundz-stems"))
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                ["python", "-m", "demucs", "--out", str(out_dir), audio_path],
                check=True,
                timeout=900,
            )
            return {"enabled": True, "engine": "demucs", "output_dir": str(out_dir)}
        except Exception as exc:
            return {"enabled": True, "engine": "demucs", "error": exc.__class__.__name__}
