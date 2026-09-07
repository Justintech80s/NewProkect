# Just Maker Core Backend 100% Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Pass 1 of the Just Maker five-subsystem hardening program so the core FastAPI backend has explicit configuration, lifecycle, readiness, job-state, request-context, and error contracts with green CI evidence.

**Architecture:** Keep the existing generation pipeline and service graph intact. Add small focused boundary modules for settings, job-state validation, API error envelopes, and dependency health; wire them into the existing `main.py`, `jobs.py`, `durable_jobs.py`, and `readiness.py` rather than creating a second application path. Backward-compatible successful response bodies stay unchanged unless the spec explicitly requires a new readiness/error contract.

**Tech Stack:** Python 3.12, FastAPI 0.116.1, Pydantic 2.11.7, pydantic-settings 2.10.1, pytest 8.4.1, PostgreSQL/psycopg where configured, existing GitHub Actions backend CI.

**Spec:** `docs/superpowers/specs/2026-09-06-just-maker-five-subsystems-100pct-design.md`

## Global Constraints

- Repository/code-complete is the target; do not claim external GPU, Kafka, embedding, or Site infrastructure is running.
- Preserve the existing generation pipeline and existing successful API contracts.
- Postgres remains authoritative; Kafka remains the event/coherence backbone contract; RocksDB remains worker-local cache.
- Externally visible errors must contain a machine code, human-safe message, request ID, and retryability indicator.
- Generation job terminal/active states are exactly `queued`, `running`, `complete`, and `failed` for this pass.
- No new TODO/TBD placeholders or silent production-dependency fallbacks.
- Every task follows TDD and must leave relevant tests green before commit.

---

## File Structure

- Create `just-soundz-backend/app/settings.py` — typed application settings and configuration validation.
- Create `just-soundz-backend/app/errors.py` — stable error payload model, typed application error, and FastAPI exception handlers.
- Create `just-soundz-backend/app/request_context.py` — request ID creation/validation and context propagation helpers.
- Create `just-soundz-backend/app/services/job_states.py` — legal job states/transitions and idempotency rules shared by in-memory and durable stores.
- Modify `just-soundz-backend/app/jobs.py` — enforce job transition contract and retain request ID.
- Modify `just-soundz-backend/app/services/durable_jobs.py` — enforce the same transition contract and persist request ID in job payload/result metadata without requiring a new schema column in this pass.
- Modify `just-soundz-backend/app/services/readiness.py` — structured dependency status (`ready`, `degraded`, `not_ready`).
- Modify `just-soundz-backend/app/main.py` — lifespan validation, middleware/context propagation, stable error handlers, readiness wiring, and background-job request ID propagation.
- Create `just-soundz-backend/tests/test_settings.py`.
- Create `just-soundz-backend/tests/test_job_states.py`.
- Create `just-soundz-backend/tests/test_readiness.py`.
- Create `just-soundz-backend/tests/test_error_contract.py`.
- Create `just-soundz-backend/tests/test_request_context.py`.
- Modify `just-soundz-backend/tests/test_jobs.py`.
- Modify `just-soundz-backend/tests/test_api_smoke.py`.

---

### Task 1: Central application settings and startup validation

**Files:**
- Create: `just-soundz-backend/app/settings.py`
- Test: `just-soundz-backend/tests/test_settings.py`
- Modify: `just-soundz-backend/app/main.py`

**Interfaces:**
- Produces: `AppSettings(BaseSettings)`, `get_settings() -> AppSettings`, `validate_startup(settings: AppSettings) -> dict[str, object]`.
- `AppSettings` owns at minimum `database_url`, `allowed_origins`, `environment`, `require_external_generator`, and configured worker URLs needed for lifecycle classification.

- [ ] **Step 1: Write failing settings tests**

```python
from app.settings import AppSettings, validate_startup


def test_allowed_origins_are_normalized():
    s = AppSettings(JUST_SOUNDZ_ALLOWED_ORIGINS="https://a.example, https://b.example")
    assert s.allowed_origins == ["https://a.example", "https://b.example"]


def test_startup_reports_missing_external_worker_without_crashing_dev():
    s = AppSettings(JUST_MAKER_ENVIRONMENT="development", JUST_MAKER_REQUIRE_EXTERNAL_GENERATOR=False)
    report = validate_startup(s)
    assert report["valid"] is True
    assert "external_generation_worker" in report["degraded"]
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_settings.py`
Expected: FAIL because `app.settings` does not exist.

- [ ] **Step 3: Implement typed settings and startup report**

Use `pydantic_settings.BaseSettings` with aliases matching current environment variables. Parse comma-separated origins into a trimmed list. `validate_startup()` must return `{valid: bool, fatal: list[str], degraded: list[str]}`; production with `require_external_generator=True` and no external worker is fatal, while development is degraded.

- [ ] **Step 4: Wire CORS and FastAPI lifespan to settings**

Replace the critical scattered CORS environment parsing in `main.py` with `settings.allowed_origins`. Add an `asynccontextmanager` lifespan that stores startup report on `app.state.startup_report`; raise `RuntimeError("invalid_startup_configuration")` only when `report["valid"]` is false.

- [ ] **Step 5: Run settings + smoke tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_settings.py tests/test_api_smoke.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add just-soundz-backend/app/settings.py just-soundz-backend/app/main.py just-soundz-backend/tests/test_settings.py
git commit -m "feat: centralize just maker application settings"
```

### Task 2: Validated and idempotent generation job state machine

**Files:**
- Create: `just-soundz-backend/app/services/job_states.py`
- Modify: `just-soundz-backend/app/jobs.py`
- Modify: `just-soundz-backend/app/services/durable_jobs.py`
- Modify: `just-soundz-backend/tests/test_jobs.py`
- Create: `just-soundz-backend/tests/test_job_states.py`

**Interfaces:**
- Produces: `JobStateError(ValueError)`, `validate_transition(current: str, target: str) -> str`, `normalize_progress(status: str, progress: float | None) -> float | None`.
- Legal transitions: `queued -> queued|running|failed`; `running -> running|complete|failed`; `complete -> complete`; `failed -> failed`. Same-state updates are explicitly idempotent.

- [ ] **Step 1: Write failing state-machine tests**

```python
import pytest
from app.services.job_states import JobStateError, validate_transition


def test_same_state_transition_is_idempotent():
    assert validate_transition("running", "running") == "running"


def test_completed_job_cannot_return_to_running():
    with pytest.raises(JobStateError):
        validate_transition("complete", "running")


def test_unknown_state_is_rejected():
    with pytest.raises(JobStateError):
        validate_transition("queued", "mystery")
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_job_states.py tests/test_jobs.py`
Expected: FAIL before implementation.

- [ ] **Step 3: Implement shared transition rules**

Create immutable legal-transition mapping. `normalize_progress` clamps active-state progress to `[0,1]`, returns `1.0` for `complete`, and never moves a terminal job backward.

- [ ] **Step 4: Enforce rules in both stores**

In `JobStore.update`, reject unknown attribute keys and invalid status transitions before mutation. In `DurableGenerationJobStore.update`, fetch the current record when configured, validate status transition before `_upsert`, and preserve terminal status on idempotent repeats. When unconfigured, validate from the explicit supplied/current status without inventing a contradictory state.

- [ ] **Step 5: Extend store tests**

Add tests proving duplicate `complete` updates are harmless, `complete -> running` raises, invalid attributes cannot be attached to the in-memory dataclass, and complete progress is `1.0`.

- [ ] **Step 6: Run focused tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_job_states.py tests/test_jobs.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add just-soundz-backend/app/services/job_states.py just-soundz-backend/app/jobs.py just-soundz-backend/app/services/durable_jobs.py just-soundz-backend/tests/test_job_states.py just-soundz-backend/tests/test_jobs.py
git commit -m "feat: validate generation job state transitions"
```

### Task 3: Request ID propagation from HTTP request through background generation

**Files:**
- Create: `just-soundz-backend/app/request_context.py`
- Modify: `just-soundz-backend/app/jobs.py`
- Modify: `just-soundz-backend/app/main.py`
- Create: `just-soundz-backend/tests/test_request_context.py`

**Interfaces:**
- Produces: `normalize_request_id(value: str | None) -> str` and `REQUEST_ID_HEADER = "X-Request-ID"`.
- `Job` gains `request_id: Optional[str]`.
- `process_job(..., request_id: str | None = None)` consumes the queued request ID rather than generating a disconnected ID internally.

- [ ] **Step 1: Write failing request-context tests**

```python
import uuid
from app.request_context import normalize_request_id


def test_missing_request_id_becomes_uuid():
    value = normalize_request_id(None)
    uuid.UUID(value)


def test_oversized_untrusted_request_id_is_replaced():
    value = normalize_request_id("x" * 500)
    assert len(value) == 36
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_request_context.py`
Expected: FAIL because helper does not exist.

- [ ] **Step 3: Implement request ID normalization**

Accept visible ASCII IDs between 1 and 128 characters; otherwise generate UUID4. Never echo control characters.

- [ ] **Step 4: Propagate request ID through API/job pipeline**

Middleware sets `request.state.request_id`. `create_job` accepts `Request`, stores the ID on the in-memory job and passes it to `process_job`. `process_job` uses the supplied ID for `operations.record` and includes it in Kafka lifecycle event payloads and result `operations.request_id`.

- [ ] **Step 5: Add API assertion**

Extend smoke/API tests so a caller-supplied valid `X-Request-ID` is echoed on the response and generated IDs are present when omitted.

- [ ] **Step 6: Run focused tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_request_context.py tests/test_api_smoke.py tests/test_jobs.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add just-soundz-backend/app/request_context.py just-soundz-backend/app/jobs.py just-soundz-backend/app/main.py just-soundz-backend/tests/test_request_context.py just-soundz-backend/tests/test_api_smoke.py
git commit -m "feat: propagate request ids through generation jobs"
```

### Task 4: Stable API error envelope

**Files:**
- Create: `just-soundz-backend/app/errors.py`
- Modify: `just-soundz-backend/app/main.py`
- Create: `just-soundz-backend/tests/test_error_contract.py`

**Interfaces:**
- Produces: `AppError(code: str, message: str, status_code: int, retryable: bool)`, `error_payload(...) -> dict`, `register_error_handlers(app: FastAPI) -> None`.
- JSON shape: `{ "error": { "code": str, "message": str, "request_id": str, "retryable": bool } }`.

- [ ] **Step 1: Write failing handler tests**

```python
def test_validation_error_uses_machine_readable_envelope(client):
    r = client.post("/v1/generate", json={"prompt": "x", "duration_seconds": 1})
    body = r.json()["error"]
    assert r.status_code == 422
    assert body["code"] == "validation_error"
    assert body["request_id"]
    assert body["retryable"] is False
```

Also test 404, authentication failure, and a synthetic `AppError(status_code=503, code="generator_unavailable", retryable=True)`.

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_error_contract.py`
Expected: FAIL because current FastAPI/HTTPException bodies use `detail`.

- [ ] **Step 3: Implement safe error handlers**

Register handlers for `AppError`, `HTTPException`, `RequestValidationError`, and uncaught `Exception`. Map known status classes to stable codes. Never return raw internal exception strings for 5xx. Obtain request ID from `request.state.request_id`.

- [ ] **Step 4: Replace exposed runtime exception detail at generation boundaries**

Where `/v1/render` and `/v1/generate` currently surface `str(exc)` from generator failures, raise `AppError(code="generator_unavailable", message="Music generation is temporarily unavailable.", status_code=503, retryable=True)` instead. Preserve detailed internal failure in operational logging/job state only.

- [ ] **Step 5: Run error and smoke tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_error_contract.py tests/test_api_smoke.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add just-soundz-backend/app/errors.py just-soundz-backend/app/main.py just-soundz-backend/tests/test_error_contract.py just-soundz-backend/tests/test_api_smoke.py
git commit -m "feat: standardize just maker api errors"
```

### Task 5: Structured dependency readiness and health contracts

**Files:**
- Modify: `just-soundz-backend/app/services/readiness.py`
- Modify: `just-soundz-backend/app/main.py`
- Create: `just-soundz-backend/tests/test_readiness.py`

**Interfaces:**
- `ReadinessChecker.check() -> dict[str, object]` returns `status`, `ready`, and `dependencies`.
- Each dependency has `name`, `required`, `status` (`ready|degraded|not_ready`), and a non-secret `reason`.
- Overall rule: any required `not_ready` => `not_ready`; otherwise any degraded/non-required unavailable dependency => `degraded`; otherwise `ready`.

- [ ] **Step 1: Write failing readiness tests with fakes**

```python
def test_missing_required_database_is_not_ready():
    checker = make_checker(database=False, worker=True, artifacts=True, auth=True)
    result = checker.check()
    assert result["status"] == "not_ready"
    assert result["ready"] is False


def test_optional_artifact_storage_gap_is_degraded():
    checker = make_checker(database=True, worker=True, artifacts=False, auth=True)
    result = checker.check()
    assert result["status"] == "degraded"
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_readiness.py`
Expected: FAIL against current boolean-only contract.

- [ ] **Step 3: Implement structured readiness**

Keep database and generation worker as required for generation readiness. Represent artifact storage and auth explicitly rather than silently omitting them. Do not expose URLs, tokens, DSNs, or secret values.

- [ ] **Step 4: Update `/ready` and `/health` behavior**

`/health` remains a liveness 200. `/ready` returns 503 only for `not_ready`; `degraded` returns 200 with `ready=True` and `status="degraded"` so operators can distinguish partial capability without treating the process as dead.

- [ ] **Step 5: Run focused tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_readiness.py tests/test_api_smoke.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add just-soundz-backend/app/services/readiness.py just-soundz-backend/app/main.py just-soundz-backend/tests/test_readiness.py just-soundz-backend/tests/test_api_smoke.py
git commit -m "feat: add structured backend readiness states"
```

### Task 6: Background-job failure hardening and final Pass 1 verification

**Files:**
- Modify: `just-soundz-backend/app/main.py`
- Modify: `just-soundz-backend/tests/test_jobs.py`
- Modify: `just-soundz-backend/tests/test_api_smoke.py`
- Create: `docs/superpowers/verification/2026-09-06-core-backend-pass1.md`

**Interfaces:**
- `process_job` must always attempt a terminal `failed` transition if any exception escapes generation/persistence/evaluation.
- Completion evidence document maps each Pass 1 acceptance criterion to code and tests.

- [ ] **Step 1: Add a failure-path test**

Patch `run_generation` to raise and call `process_job` synchronously with a created in-memory job. Assert final state is `failed`, error is present internally, and the state is never left `running`.

- [ ] **Step 2: Run the new test and confirm current behavior/gap**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_jobs.py`
Expected before any needed fix: the new assertion identifies any stranded-state or invalid-transition issue.

- [ ] **Step 3: Harden `process_job` finalization**

Use the shared job-state transition helper for both complete and failed updates. Failure-event publishing and metrics must be best-effort and must not prevent the job store from receiving its terminal failure state. Keep raw exception detail out of HTTP responses.

- [ ] **Step 4: Run full backend test suite**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests`
Expected: PASS with zero failures.

- [ ] **Step 5: Compile all backend modules**

Run: `cd just-soundz-backend && python -m compileall -q app tests`
Expected: exit 0.

- [ ] **Step 6: Create verification matrix**

Document the ten Pass 1 acceptance criteria from the spec and, for each, list the exact implementation file(s), exact test file(s), and verified status. Do not mark a criterion complete without evidence.

- [ ] **Step 7: Check for new placeholders and duplicate boundary implementations**

Run:
```bash
git grep -nE 'TODO|TBD|implement later' -- just-soundz-backend/app just-soundz-backend/tests docs/superpowers/verification || true
git grep -nE 'class (AppSettings|JobStateError|AppError|ReadinessChecker)' -- just-soundz-backend/app
```
Expected: no new placeholder hits; one intended implementation per boundary type.

- [ ] **Step 8: Commit**

```bash
git add just-soundz-backend/app just-soundz-backend/tests docs/superpowers/verification/2026-09-06-core-backend-pass1.md
git commit -m "test: verify core backend pass one completion"
```

- [ ] **Step 9: Push/open PR and require green backend CI**

The PR is not merge-ready until `Just Maker Backend CI` completes successfully on the final head commit. If CI fails, diagnose and fix the actual failure; do not weaken the test or readiness requirement to force green status.
