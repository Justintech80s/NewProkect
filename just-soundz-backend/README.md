# Just Soundz AI Companion Backend

Backend-only upgrade layer for the existing Just Soundz AI Companion. It is intentionally isolated from the website's frontend, so the visual design does not need to change.

## Added architecture

- Structured AI producer/planning layer for BPM, key, harmony, drums, bass, arrangement and duration.
- Interchangeable generation router so music models/providers can be swapped without rewriting the website.
- Adapter point for JASCO/MusicGen-style conditioning.
- Adapter point for Stable Audio-style generation workers.
- Essentia-compatible BPM/key/audio analysis.
- CLAP-compatible text-to-audio quality scoring.
- Automatic retry of weak generations.
- Optional Demucs stem separation.
- FastAPI endpoint: `POST /v1/generate`.
- Health endpoint: `GET /health`.

## Important model/license design

This repository does not bundle third-party model weights. Some open-source repositories publish code under permissive licenses while distributing particular trained weights under more restrictive terms. Production should use only model weights/services whose licenses permit the intended Just Soundz use.

## Run locally

```bash
cd just-soundz-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The current website can keep its existing layout and controls. Its Generate action only needs to call this backend once a deployed endpoint and approved music-generation worker are configured.
