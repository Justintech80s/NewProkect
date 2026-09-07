# Just Maker Five-Subsystem 100% Completion Design

Date: 2026-09-06

## Goal

Bring these five areas to **repository/code-complete 100%** before adding more product features:

1. Core backend architecture
2. Security/auth/job ownership
3. DSP/mastering/stems architecture
4. Music Brain / dataset intelligence
5. Composition API integration

"100%" in this design means there are no known code-level gaps inside these five areas, the required interfaces are implemented, tests and CI cover the critical paths, failure modes are explicit, operational requirements are documented, and placeholder or silent-fallback behavior is removed where it would hide a broken production dependency. External services that require separate provisioning are represented by strict adapters, readiness checks, and documented deployment contracts rather than falsely treated as running.

## Approach

Use five sequential hardening passes on top of the current main branch. Each pass must leave the repository green before the next begins. Changes should reuse existing services instead of introducing parallel implementations.

### Pass 1 — Core backend architecture

Complete the application boundary and lifecycle behavior.

Acceptance criteria:
- FastAPI startup/shutdown lifecycle validates critical configuration.
- Central application settings object replaces scattered critical environment parsing where practical.
- Readiness distinguishes `ready`, `degraded`, and `not_ready` dependencies.
- Generation job state transitions are validated and idempotent.
- Background job failures cannot silently strand jobs in `running` state.
- Request IDs propagate into generation jobs and operational events.
- API errors use a stable machine-readable error envelope.
- Core service dependencies expose health/readiness contracts.
- Existing generation pipeline remains backward compatible.
- Unit and API tests cover startup, readiness, state transitions, idempotency, and error envelopes.

### Pass 2 — Security / auth / job ownership

Make authenticated ownership and private artifact access consistent across all user-scoped endpoints.

Acceptance criteria:
- Every user-scoped job, retry, feedback, artifact, preference, memory, and usage endpoint requires authenticated user context.
- Job ownership is verified using the durable store when configured and safe in-memory ownership otherwise.
- Cross-user job/artifact access returns 404-style isolation rather than leaking existence.
- Signed artifact URLs are short-lived, ownership checked, and bounded to a safe expiry range.
- Public endpoints are explicitly classified and documented.
- Input validation prevents oversized prompts, unsafe filenames/path traversal, malformed artifact IDs, and invalid state values.
- Security headers and CORS are explicit and environment-driven.
- Authentication failures never leak token contents or provider internals.
- Rate/quota and concurrency enforcement are tested for authenticated users.
- Security regression tests cover cross-user access, unsigned artifact access, token failure, CORS, and path handling.

### Pass 3 — DSP / mastering / stems architecture

Make the local audio-processing path deterministic, measurable, and fail-safe.

Acceptance criteria:
- Rust DSP path and NumPy fallback produce compatible bounded outputs for the same fixtures.
- Mastering validates sample format, channels, duration, finite values, peak bounds, and output existence.
- Stem mixer validates all requested stems and reports partial/missing stem conditions explicitly.
- Gain staging prevents clipping before and after mixdown.
- Mastering critic has deterministic thresholds and corrective-pass caps.
- DSP failures cannot overwrite or delete the original render.
- Generated master and stems carry structured technical metadata.
- Tests include silence, clipped audio, DC offset, short files, malformed files, missing stems, and multi-stem mix fixtures.
- Rust CI and Python audio tests both pass.

### Pass 4 — Music Brain / dataset intelligence

Finish data-quality, rights, provenance, retrieval, and embedding boundaries.

Acceptance criteria:
- Every ingested record has provenance, rights status, source identity, deterministic fingerprint, and ingestion timestamp.
- Duplicate handling is deterministic across resumed/imported batches.
- Reference-only metadata cannot become sample-eligible without an explicit rights transition.
- User-owned and licensed/cleared audio are the only categories eligible for sample-audio embedding/search paths.
- Dataset manifests validate schema version and reject incompatible records cleanly.
- Ingestion checkpoints are resumable and idempotent.
- Embedding dimension and model-space compatibility are validated before vector writes/search.
- Search results expose provenance and rights information needed by downstream policy.
- Cache invalidation is emitted after successful authoritative writes only.
- Tests cover duplicate ingestion, resume, rights escalation denial, embedding mismatch, invalid manifests, and provenance persistence.

### Pass 5 — Composition API integration

Make the frontend-to-backend contract complete and stable.

Acceptance criteria:
- Composition client has one canonical request normalizer for prompt, genre, mood, BPM, key, duration, stems, quality, and candidate controls.
- Job creation returns a stable response contract with job ID, status, and polling metadata.
- Polling exposes stage, progress, result, error, and artifacts consistently.
- Completed master artifacts can be resolved to signed playback/download URLs.
- Retry behavior is bounded and preserves lineage (`retry_of`, retry count).
- Client distinguishes authentication, quota, service-unavailable, generation-failed, and network errors.
- Cancellation is explicitly unsupported or implemented; no ambiguous UI contract.
- API schema/examples are documented for the Site integration.
- Browser-side client tests cover queue → poll → complete → signed URL, quota failure, auth failure, generation failure, retry, and timeout.
- Backend CI and Composition Client CI pass together.

## Data Flow

Composition UI -> Composition client -> authenticated `/v1/jobs` -> durable job state -> generation pipeline -> GPU/router contract -> DSP/mastering/stem processing -> artifact persistence -> signed artifact URL -> Composition player/download.

Music Brain participates during generation planning only through rights-aware reference and sample-eligible retrieval. Postgres remains authoritative; Kafka remains the event/coherence backbone contract; RocksDB remains a worker-local cache and must never become authoritative.

## Error Handling

All externally visible failures should map to a stable error payload containing a machine code, human-safe message, request ID, and retryability indicator. Internal exception strings must not be returned directly when they may expose infrastructure details.

Generation jobs must end in one of: `queued`, `running`, `complete`, or `failed`. Unknown and contradictory states are rejected. Failed jobs retain enough metadata for controlled retry without exposing secrets.

## Testing Strategy

Each pass adds focused unit tests plus integration/API tests. Existing CI remains mandatory. New tests should prefer deterministic fixtures and dependency fakes over network services. Where a real service matters to correctness, existing integration workflows (Kafka, RocksDB, Rust) remain as separate CI gates.

Before declaring the five areas complete:
- all relevant GitHub Actions workflows must be successful on the final head commit;
- no failing security tests;
- no TODO/TBD placeholders in the new hardening code or docs;
- repository search confirms no duplicate competing implementation was introduced;
- final completion matrix maps every acceptance criterion to code/tests.

## Out of Scope for This 100% Pass

These are external production-delivery tasks and are not counted as repository/code gaps:
- provisioning a permanent GPU service;
- provisioning a permanent production Kafka cluster;
- deploying a persistent production audio-embedding worker;
- editing/publishing the live ChatGPT Site while its editor is unavailable;
- choosing or changing a hosting provider.

The repository must nevertheless include strict configuration, readiness, error handling, and deployment contracts for those services.

## Completion Rule

A subsystem reaches 100% only when its acceptance criteria are implemented, covered by tests, and the relevant CI is green. Percentages are not raised merely because code exists; evidence must be present in the final verification matrix.
