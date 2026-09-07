# Just Maker GPU Music Worker

Phase 21 adds a deployable GPU generation service for the Just Maker backend.

## API

- GET /health
- GET /capabilities
- POST /generate
- GET /artifacts/{filename}

POST /generate accepts the full Just Maker generation plan plus the structured conditioning payload produced by the Producer DNA, rhythm, harmony, instrumentation, arrangement and Music Brain layers.

## GPU worker environment

Required:

- JUST_MAKER_GPU_MODEL_ID
- JUST_MAKER_GPU_WORKER_TOKEN
- JUST_MAKER_GPU_BACKEND=transformers-musicgen
- JUST_MAKER_GPU_DEVICE=cuda

Optional:

- JUST_MAKER_GPU_MAX_SECONDS=180
- JUST_MAKER_GPU_OUTPUT_DIR=/tmp/just-maker-gpu

The selected model ID is intentionally not hard-coded. Only deploy model weights whose license permits the intended use.

## Connect to the main backend

After deploying this container to a CUDA-capable host, set on the Just Maker backend:

- JUST_SOUNDZ_PRIMARY_WORKER_URL=https://your-gpu-worker
- JUST_SOUNDZ_PRIMARY_WORKER_TOKEN=<same private token>

The existing capability-aware router will rank this GPU service against other configured workers and automatically fail over if needed.

## Docker

Build:

docker build -t just-maker-gpu-worker .

Run on a CUDA host:

docker run --gpus all -p 8080:8080 \
  -e JUST_MAKER_GPU_MODEL_ID=<approved-model-id> \
  -e JUST_MAKER_GPU_WORKER_TOKEN=<secret> \
  just-maker-gpu-worker

## Replicate GPU deployment

Just Maker can run the heavyweight music model on Replicate while keeping the normal API/backend on Vercel.

### Replicate model package

The GPU worker directory contains:

- `cog.yaml` — Cog GPU image definition.
- `predict.py` — Replicate prediction interface.
- `worker.py` — existing Just Maker generation runtime and Pass 6 conditioning.
- `.github/workflows/replicate-gpu-push.yml` — manual GitHub Action that pushes the Cog model.

The model ID is intentionally not hard-coded. Configure `JUST_MAKER_GPU_MODEL_ID` on the Replicate deployment with a model whose license permits your intended use.

### Main backend environment

After the Replicate model has been pushed and a deployment has been created, configure the Vercel backend with:

- `JUST_SOUNDZ_REPLICATE_DEPLOYMENT=owner/deployment-name`
- `JUST_SOUNDZ_REPLICATE_API_TOKEN=<private token>`

The Replicate deployment is ranked ahead of the lightweight Vercel worker. The backend checks deployment health, submits the full plan + conditioning JSON, polls long-running predictions, securely downloads the returned audio artifact, and then continues through Just Maker's existing analysis/mastering/artifact pipeline.
