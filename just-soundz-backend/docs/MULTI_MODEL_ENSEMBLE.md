# Just Maker multi-model GPU ensemble

Phase 47 allows Just Maker to register multiple independently deployed,
appropriately licensed generation workers and route each request to the worker
with the strongest combination of capabilities, historical quality, context,
genre specialization and duration support.

## Register workers

Use:

`JUST_MAKER_ENSEMBLE_WORKERS=name|kind|url_env|token_env|priority;...`

Example:

`JUST_MAKER_ENSEMBLE_WORKERS=hiphop-gpu|http-worker|HIPHOP_URL|HIPHOP_TOKEN|12;cinematic-gpu|stable-audio-worker|CINEMATIC_URL|CINEMATIC_TOKEN|14`

Then provide the referenced URL/token environment variables on the runtime host.

Supported kinds:

- `http-worker`
- `musicgen-jasco-worker`
- `stable-audio-worker`

## Specialization

A worker can receive a small routing bonus for genres it is specifically
validated for:

`JUST_MAKER_HIPHOP_GPU_GENRES=hip-hop,boom-bap,trap`

This does not override capability or duration requirements. Historical
evaluation data remains part of the routing score.

## Licensing

The registry deliberately stores endpoints and capabilities, not model weights.
Only deploy models whose licenses permit the intended Just Maker use.

## Architecture

Prompt/plan -> capability requirements -> model ensemble ranking -> selected GPU
worker -> evaluation -> historical performance -> future routing.

This keeps model selection plug-and-play and avoids coupling Just Maker to one
music-generation model.
