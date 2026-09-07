# Just Maker Core Backend Pass 1 Verification

Date: 2026-09-06
PR: #52 — Pass 1: Core backend architecture hardening
Scope: repository/code-complete core backend architecture only. External GPU, production Kafka, embedding-worker, hosting, and ChatGPT Site provisioning remain separate production-delivery tasks.

| Acceptance criterion | Implementation evidence | Test / CI evidence | Status |
|---|---|---|---|
| Startup/shutdown lifecycle validates critical configuration | `app/settings.py`; FastAPI `lifespan` in `app/main.py` stores `app.state.startup_report` and rejects invalid startup configuration | `tests/test_settings.py`; `tests/test_api_smoke.py::test_lifespan_sets_startup_report` | PASS |
| Centralized critical application settings | `app/settings.py` owns environment, database URL, CORS origins, external-generator requirement, direct worker endpoints, and ensemble configuration; blank CORS origin sets are rejected | `tests/test_settings.py` covers normalization, blank rejection, direct/external-worker requirement, and ensemble endpoint configuration | PASS |
| Three-state dependency readiness | `app/services/readiness.py` exposes dependency-level `ready`, `degraded`, and `not_ready` states; database and generation worker are required, artifact storage and auth are explicitly classified | `tests/test_readiness.py` covers required DB/worker failures, optional degradation, and fully ready state | PASS |
| Validated/idempotent job transitions | `app/services/job_states.py`, `app/jobs.py`, and `app/services/durable_jobs.py` enforce four persisted states and legal transitions; same-state terminal updates are idempotent | `tests/test_job_states.py`; `tests/test_jobs.py` cover same-state updates, illegal rollback, invalid state, invalid field, and complete progress | PASS |
| No stranded `running` jobs after generation failure | `process_job` in `app/main.py` makes event/metrics/usage failure reporting best-effort and protects terminal failure writes with an in-memory `finally` update | `tests/test_jobs.py::test_process_job_failure_cannot_leave_running` | PASS |
| Request-ID propagation | `app/request_context.py`; request middleware, job creation/retry, `process_job`, operational metrics, result metadata, and Kafka lifecycle payloads in `app/main.py`; `Job.request_id` in `app/jobs.py` | `tests/test_request_context.py`; request-ID echo tests in `tests/test_api_smoke.py`; failure-path job test verifies retained request ID | PASS |
| Stable machine-readable API error envelope | `app/errors.py` handles application, validation, Starlette routing/HTTP, and unexpected exceptions with `{error:{code,message,request_id,retryable}}`; generation boundaries use safe `generator_unavailable` errors | `tests/test_error_contract.py` covers validation, routing 404, auth/service failure, and retryable synthetic 503 | PASS |
| Core service health/readiness contract | `/health` remains liveness-only 200; `/ready` returns 503 only for `not_ready`, while degraded service remains observable as 200 with structured dependency details | `tests/test_readiness.py`; `tests/test_api_smoke.py::test_health_contract` | PASS |
| Existing generation pipeline remains backward compatible | Core generation planner/router/DSP/evaluation flow in `app/main.py` is retained; changes are limited to boundary/lifecycle/error/context integration | Full `pytest -q tests` completed successfully during Pass 1 integration run before the integrated `main.py` commit; final PR CI repeats the full suite | PASS |
| Unit/API coverage and hardening hygiene | Focused tests added for settings, lifecycle, job states, request context, errors, readiness, and failure finalization; `.github/workflows/just-maker-backend-ci.yml` now compiles, runs full tests/API smoke, rejects new hardening TODO/TBD placeholders, and rejects duplicate boundary-class definitions | Final merge requires `Just Maker Backend CI` backend-tests, GPU-contract, and security-contract jobs to be green on the final PR head | PASS |

## Persisted job-state contract

Only these states are persisted by this pass: `queued`, `running`, `complete`, and `failed`.

Legal transitions are:
- `queued -> queued | running | failed`
- `running -> running | complete | failed`
- `complete -> complete`
- `failed -> failed`

A stale heartbeat on a `running` job is a recovery condition, not a fifth `stalled` state. `JobRecoveryPlanner` may classify a stale running job as retryable without mutating its stored state.

## Error contract

Externally visible JSON errors use:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Human-safe message.",
    "request_id": "trace-id",
    "retryable": false
  }
}
```

Internal infrastructure exception strings are not returned by generic 5xx handlers. Generator unavailability is exposed as a safe retryable 503. Authentication-provider unavailability remains categorized as service unavailability rather than a generation failure.

## Final merge gate

Pass 1 is eligible to merge only when the normal `Just Maker Backend CI` workflow is successful on the final PR head, including:
1. backend compile + full test suite + API smoke + hardening scan;
2. GPU worker contract tests;
3. security contract checks.

No production-infrastructure claim is implied by this repository-completion matrix.
