# Just Maker production deployment checklist

This checklist is for the backend and GPU worker. It does not change the website UI.

## Required before production traffic

- GitHub Actions backend CI is green.
- Supabase migrations are applied.
- JUST_MAKER_DATABASE_URL is configured on the backend.
- JUST_MAKER_SUPABASE_URL is configured.
- JUST_MAKER_SUPABASE_SERVICE_ROLE_KEY is stored only as a deployment secret.
- JUST_MAKER_SUPABASE_PUBLISHABLE_KEY is configured for user-token validation.
- The just-maker-artifacts bucket remains private.
- A CUDA-capable GPU worker is deployed.
- JUST_SOUNDZ_PRIMARY_WORKER_URL points to that worker.
- Worker bearer tokens match and are stored only as deployment secrets.
- The selected music model's license is approved for the intended use.
- GET /health returns HTTP 200.
- GET /ready returns HTTP 200 after production dependencies are connected.
- A test generation completes and produces a persisted master artifact.
- Signed artifact delivery succeeds for the owning authenticated user.
- A second user cannot access the first user's job or artifact.
- Provider evaluation metrics begin recording.
- Operational event metrics begin recording.
- Cost-per-GPU-second is adjusted to the actual infrastructure rate.

## Release verification

Run one short generation with stems enabled and verify:

1. Music Brain retrieval completes.
2. Producer DNA and advanced conditioning are populated.
3. A GPU worker is selected when configured.
4. Native stems are generated or fallback generation succeeds.
5. Mix intelligence and mastering complete.
6. Production Critic and automated evaluation run.
7. Master and stems persist to private storage.
8. The signed URL endpoint returns a temporary URL only for the owner.
9. Operational metrics record latency, success and estimated cost.
10. No secrets appear in logs or repository files.
