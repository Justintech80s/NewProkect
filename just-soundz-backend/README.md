# Just Soundz AI Companion Backend

Backend-only upgrade layer for the existing Just Soundz AI Companion. It is intentionally isolated from the website's frontend, so the visual design does not need to change.

## Architecture

- Structured AI producer/planning layer for BPM, key, harmony, drums, bass, arrangement and duration.
- Interchangeable generation router.
- Dedicated provider adapters for generic HTTP workers, MusicGen/JASCO-style workers and Stable-Audio-style workers.
- Standard GPU-worker request/response contract.
- Essentia-compatible BPM/key/audio analysis.
- CLAP-compatible text-to-audio quality scoring.
- Automatic retry of weak generations.
- Optional Demucs stem separation.
- Synchronous generation endpoint: `POST /v1/generate`.
- Background job endpoint: `POST /v1/jobs`.
- Job status endpoint: `GET /v1/jobs/{job_id}`.
- Health endpoint: `GET /health`.
- Basic automated tests for producer planning and job lifecycle.

## Why the job API matters

Full-length AI music can take much longer than an ordinary web request. The job API lets the existing app submit a generation request, receive a job ID immediately, and check status until the instrumental is ready. This can be connected without redesigning the current website or phone interface.

## Provider configuration

```bash
JUST_SOUNDZ_GENERATOR=musicgen-jasco-worker
JUST_SOUNDZ_WORKER_URL=https://your-approved-gpu-worker.example.com
JUST_SOUNDZ_WORKER_TOKEN=replace-me
```

Other supported router labels are:

- `http-worker`
- `stable-audio-worker`

The actual worker may use any commercially permitted music-generation engine that follows the documented contract in `worker/README.md`.

## Important model/license design

This repository does not bundle third-party model weights. Production should use only model weights/services whose licenses permit the intended Just Soundz use.

## Run locally

```bash
cd just-soundz-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The existing Just Soundz interface can remain visually unchanged. The Create action only needs to call this backend once a deployed endpoint and approved music-generation worker are configured.
