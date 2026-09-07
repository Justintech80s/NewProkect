# Just Maker Core Backend 100% Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Pass 1 of the Just Maker five-subsystem hardening program so the core FastAPI backend has explicit configuration, lifecycle, readiness, job-state, request-context, and error contracts with green CI evidence.

**Architecture:** Preserve the existing generation pipeline and service graph. Add focused boundary modules for settings, job-state validation, request context, and API errors; wire them into `main.py`, `jobs.py`, `durable_jobs.py`, `job_recovery.py`, and `readiness.py`. Successful generation contracts remain backward compatible; new structure is limited to startup/readiness and error behavior required by the approved spec.

**Tech Stack:** Python 3.12, FastAPI 0.116.1, Pydantic 2.11.7, pydantic-settings 2.10.1, pytest 8.4.1, PostgreSQL/psycopg where configured, existing GitHub Actions backend CI.

**Spec:** `docs/superpowers/specs/2026-09-06-just-maker-five-subsystems-100pct-design.md`

## Global Constraints

- Repository/code-complete is the target; external GPU, Kafka, embedding, and Site infrastructure are not represented as running.
- Preserve the existing generation pipeline and existing successful API response contracts.
- Postgres remains authoritative; Kafka remains the event/coherence backbone contract; RocksDB remains worker-local cache.
- Externally visible errors contain a machine code, human-safe message, request ID, and retryability indicator.
- Persisted generation job states are exactly `queued`, `running`, `complete`, and `failed`.
- Staleness is metadata/condition on a `running` job, not a fifth persisted state.
- No unfinished placeholders or silent fallback that would hide a broken required production dependency.
- Each task follows TDD and must leave its focused tests green before commit.

---

## File Structure

- Create `just-soundz-backend/app/settings.py` — typed application settings and startup validation.
- Create `just-soundz-backend/app/errors.py` — stable error envelope and exception handlers.
- Create `just-soundz-backend/app/request_context.py` — request-ID normalization and propagation helper.
- Create `just-soundz-backend/app/services/job_states.py` — four-state transition and idempotency contract.
- Modify `just-soundz-backend/app/jobs.py` — enforce state rules and retain request ID.
- Modify `just-soundz-backend/app/services/durable_jobs.py` — enforce the same state rules for persisted jobs.
- Modify `just-soundz-backend/app/services/job_recovery.py` — retry failed jobs and stale-running jobs without persisting a `stalled` state.
- Modify `just-soundz-backend/app/services/readiness.py` — `ready`, `degraded`, and `not_ready` dependency contract.
- Modify `just-soundz-backend/app/main.py` — lifespan, settings, request context, error handlers, readiness, and background-job propagation.
- Create `just-soundz-backend/tests/test_settings.py`.
- Create `just-soundz-backend/tests/test_job_states.py`.
- Create `just-soundz-backend/tests/test_request_context.py`.
- Create `just-soundz-backend/tests/test_error_contract.py`.
- Create `just-soundz-backend/tests/test_readiness.py`.
- Modify `just-soundz-backend/tests/test_jobs.py`.
- Modify `just-soundz-backend/tests/test_api_smoke.py`.
- Create `docs/superpowers/verification/2026-09-06-core-backend-pass1.md`.

---

### Task 1: Central application settings and lifecycle validation

**Files:**
- Create: `just-soundz-backend/app/settings.py`
- Modify: `just-soundz-backend/app/main.py`
- Test: `just-soundz-backend/tests/test_settings.py`

**Interfaces:**
- Produces `AppSettings(BaseSettings)`.
- Produces `get_settings() -> AppSettings`.
- Produces `validate_startup(settings: AppSettings) -> dict[str, object]` with keys `valid`, `fatal`, and `degraded`.

- [ ] **Step 1: Write failing tests**

```python
from app.settings import AppSettings, validate_startup


def test_allowed_origins_are_normalized():
    settings = AppSettings(
        JUST_SOUNDZ_ALLOWED_ORIGINS="https://a.example, https://b.example"
    )
    assert settings.allowed_origins == ["https://a.example", "https://b.example"]


def test_missing_external_worker_is_degraded_in_development():
    settings = AppSettings(
        JUST_MAKER_ENVIRONMENT="development",
        JUST_MAKER_REQUIRE_EXTERNAL_GENERATOR=False,
    )
    report = validate_startup(settings)
    assert report["valid"] is True
    assert "external_generation_worker" in report["degraded"]


def test_required_external_worker_is_fatal_when_missing():
    settings = AppSettings(
        JUST_MAKER_ENVIRONMENT="production",
        JUST_MAKER_REQUIRE_EXTERNAL_GENERATOR=True,
    )
    report = validate_startup(settings)
    assert report["valid"] is False
    assert "external_generation_worker" in report["fatal"]
```

- [ ] **Step 2: Verify failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_settings.py`
Expected: FAIL because `app.settings` does not exist.

- [ ] **Step 3: Implement typed settings**

Use `pydantic_settings.BaseSettings` and aliases matching the existing environment variables. The settings object owns at minimum database URL, allowed origins, environment, external-generator requirement, primary worker URL, MusicGen worker URL, Stable Audio worker URL, and ensemble configuration. Normalize origins into a trimmed list and reject blank origins.

- [ ] **Step 4: Add FastAPI lifespan validation**

Use `asynccontextmanager`. At startup run `validate_startup(settings)` and place the report on `app.state.startup_report`. Raise `RuntimeError("invalid_startup_configuration")` only when `valid` is false. Shutdown must not discard pending job state or mutate terminal jobs.

- [ ] **Step 5: Move CORS to settings**

`main.py` consumes `settings.allowed_origins`; remove its duplicated direct parsing of `JUST_SOUNDZ_ALLOWED_ORIGINS`.

- [ ] **Step 6: Verify focused tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_settings.py tests/test_api_smoke.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add just-soundz-backend/app/settings.py just-soundz-backend/app/main.py just-soundz-backend/tests/test_settings.py
git commit -m "feat: centralize just maker application settings"
```

### Task 2: Four-state idempotent job lifecycle

**Files:**
- Create: `just-soundz-backend/app/services/job_states.py`
- Modify: `just-soundz-backend/app/jobs.py`
- Modify: `just-soundz-backend/app/services/durable_jobs.py`
- Modify: `just-soundz-backend/app/services/job_recovery.py`
- Create: `just-soundz-backend/tests/test_job_states.py`
- Modify: `just-soundz-backend/tests/test_jobs.py`

**Interfaces:**
- Produces `JobStateError(ValueError)`.
- Produces `validate_transition(current: str, target: str) -> str`.
- Produces `normalize_progress(status: str, progress: float | None) -> float | None`.
- Legal transitions: `queued -> queued|running|failed`, `running -> running|complete|failed`, `complete -> complete`, `failed -> failed`.
- Same-state transitions are idempotent.
- `JobRecoveryPlanner.assess()` treats a stale heartbeat on `running` as retryable without changing persisted state to `stalled`.

- [ ] **Step 1: Write failing state tests**

```python
import pytest
from app.services.job_states import JobStateError, validate_transition


def test_running_to_running_is_idempotent():
    assert validate_transition("running", "running") == "running"


def test_complete_cannot_return_to_running():
    with pytest.raises(JobStateError):
        validate_transition("complete", "running")


def test_unknown_state_is_rejected():
    with pytest.raises(JobStateError):
        validate_transition("queued", "stalled")
```

Add recovery coverage:

```python
from datetime import datetime, timedelta, timezone
from app.services.job_recovery import JobRecoveryPlanner


def test_stale_running_job_is_retryable_without_fifth_state():
    planner = JobRecoveryPlanner(stale_after_seconds=60)
    old = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    result = planner.assess({
        "status": "running",
        "heartbeat_at": old,
        "retry_count": 0,
        "max_retries": 3,
    })
    assert result["retryable"] is True
    assert result["reason"] == "stale_running_job"
```

- [ ] **Step 2: Verify failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_job_states.py tests/test_jobs.py`
Expected: FAIL before implementation.

- [ ] **Step 3: Implement transition rules**

Create an immutable legal-transition map. Validate both current and target values. `normalize_progress` clamps active-state progress to `[0.0, 1.0]`, forces `complete` to `1.0`, and never makes a terminal state active again.

- [ ] **Step 4: Enforce transition rules in both stores**

`JobStore.update` validates keys and transitions before mutating the dataclass. `DurableGenerationJobStore.update` validates against the current persisted status when configured and refuses contradictory transitions. Idempotent duplicate terminal writes remain safe.

- [ ] **Step 5: Reconcile recovery behavior**

Replace `RETRYABLE_STATUSES = {"failed", "stalled"}` with failed-state plus stale-running evaluation. Constructor accepts `stale_after_seconds` with a bounded positive default. A fresh running job remains non-retryable.

- [ ] **Step 6: Extend store tests**

Verify duplicate `complete` updates, `complete -> running` rejection, invalid attribute rejection, complete progress `1.0`, failed-job retry eligibility, stale-running retry eligibility, and fresh-running rejection.

- [ ] **Step 7: Verify focused tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_job_states.py tests/test_jobs.py`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add just-soundz-backend/app/services/job_states.py just-soundz-backend/app/jobs.py just-soundz-backend/app/services/durable_jobs.py just-soundz-backend/app/services/job_recovery.py just-soundz-backend/tests/test_job_states.py just-soundz-backend/tests/test_jobs.py
git commit -m "feat: enforce four state generation lifecycle"
```

### Task 3: Request ID propagation

**Files:**
- Create: `just-soundz-backend/app/request_context.py`
- Modify: `just-soundz-backend/app/jobs.py`
- Modify: `just-soundz-backend/app/main.py`
- Test: `just-soundz-backend/tests/test_request_context.py`
- Modify: `just-soundz-backend/tests/test_api_smoke.py`

**Interfaces:**
- Produces `REQUEST_ID_HEADER = "X-Request-ID"`.
- Produces `normalize_request_id(value: str | None) -> str`.
- `Job` gains `request_id: Optional[str]`.
- `process_job(job_id, req, user_id=None, request_id=None)` uses the queued request ID for all operational lifecycle records.

- [ ] **Step 1: Write failing helper tests**

```python
import uuid
from app.request_context import normalize_request_id


def test_missing_id_becomes_uuid4_shape():
    value = normalize_request_id(None)
    uuid.UUID(value)


def test_control_character_id_is_replaced():
    value = normalize_request_id("bad\nheader")
    assert "\n" not in value
    assert len(value) == 36


def test_valid_caller_id_is_preserved():
    assert normalize_request_id("site-req-123") == "site-req-123"
```

- [ ] **Step 2: Verify failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_request_context.py`
Expected: FAIL because helper does not exist.

- [ ] **Step 3: Implement normalization**

Accept visible ASCII values from 1 through 128 characters; otherwise generate UUID4. The helper never returns control characters.

- [ ] **Step 4: Propagate request ID through HTTP and background generation**

Middleware sets `request.state.request_id` and echoes it as `X-Request-ID`. `create_job` passes it into in-memory job creation and `process_job`. `process_job` stops generating a disconnected internal ID and uses the propagated value for operational metrics, Kafka lifecycle payloads, and `result["operations"]["request_id"]`.

- [ ] **Step 5: Add API assertions**

Test valid caller ID echo and generated ID echo. Keep existing authenticated-job behavior intact.

- [ ] **Step 6: Verify focused tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_request_context.py tests/test_api_smoke.py tests/test_jobs.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add just-soundz-backend/app/request_context.py just-soundz-backend/app/jobs.py just-soundz-backend/app/main.py just-soundz-backend/tests/test_request_context.py just-soundz-backend/tests/test_api_smoke.py
git commit -m "feat: propagate request ids through generation jobs"
```

### Task 4: Stable API error contract

**Files:**
- Create: `just-soundz-backend/app/errors.py`
- Modify: `just-soundz-backend/app/main.py`
- Test: `just-soundz-backend/tests/test_error_contract.py`
- Modify: `just-soundz-backend/tests/test_api_smoke.py`

**Interfaces:**
- Produces `AppError(code: str, message: str, status_code: int, retryable: bool)`.
- Produces `error_payload(code, message, request_id, retryable) -> dict[str, object]`.
- Produces `register_error_handlers(app: FastAPI) -> None`.
- Response shape is `{"error":{"code":str,"message":str,"request_id":str,"retryable":bool}}`.

- [ ] **Step 1: Write failing API error tests**

```python
def test_validation_error_has_stable_envelope(client):
    response = client.post("/v1/generate", json={
        "prompt": "x",
        "duration_seconds": 1,
    })
    error = response.json()["error"]
    assert response.status_code == 422
    assert error["code"] == "validation_error"
    assert error["request_id"]
    assert error["retryable"] is False
```

Also assert stable envelopes for 404, missing authentication, and a synthetic retryable 503 `AppError`.

- [ ] **Step 2: Verify failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_error_contract.py`
Expected: FAIL because current framework errors expose `detail`.

- [ ] **Step 3: Implement exception handlers**

Handle `AppError`, FastAPI/Starlette `HTTPException`, `RequestValidationError`, and uncaught `Exception`. Read request ID from `request.state.request_id`. For 5xx responses return only safe generic messages; never return worker URLs, tokens, DSNs, stack traces, or raw infrastructure exception strings.

- [ ] **Step 4: Convert generator boundary failures**

`/v1/render` and `/v1/generate` convert generation `RuntimeError` into `AppError(code="generator_unavailable", message="Music generation is temporarily unavailable.", status_code=503, retryable=True)`. Internal job/operations records may retain diagnostic class/reason data.

- [ ] **Step 5: Verify focused tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_error_contract.py tests/test_api_smoke.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add just-soundz-backend/app/errors.py just-soundz-backend/app/main.py just-soundz-backend/tests/test_error_contract.py just-soundz-backend/tests/test_api_smoke.py
git commit -m "feat: standardize just maker api errors"
```

### Task 5: Structured dependency readiness

**Files:**
- Modify: `just-soundz-backend/app/services/readiness.py`
- Modify: `just-soundz-backend/app/main.py`
- Test: `just-soundz-backend/tests/test_readiness.py`
- Modify: `just-soundz-backend/tests/test_api_smoke.py`

**Interfaces:**
- `ReadinessChecker.check() -> dict[str, object]` returns `status`, `ready`, and `dependencies`.
- Each dependency entry contains `name`, `required`, `status`, and non-secret `reason`.
- Status values are `ready`, `degraded`, or `not_ready`.

- [ ] **Step 1: Write failing readiness tests**

```python
def test_required_database_gap_is_not_ready(make_checker):
    result = make_checker(database=False, worker=True, artifacts=True, auth=True).check()
    assert result["status"] == "not_ready"
    assert result["ready"] is False


def test_optional_artifact_gap_is_degraded(make_checker):
    result = make_checker(database=True, worker=True, artifacts=False, auth=True).check()
    assert result["status"] == "degraded"
    assert result["ready"] is True
```

The fixture supplies tiny fakes exposing only the existing `.configured`/`.status()` interfaces.

- [ ] **Step 2: Verify failure**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_readiness.py`
Expected: FAIL against the current boolean-only checker.

- [ ] **Step 3: Implement dependency records**

Database and generation-worker availability remain required for generation readiness. Artifact storage and authentication are explicit dependencies; if absent they produce degraded state in this Pass 1 contract. Reasons are symbolic strings such as `not_configured` or `no_generation_worker`; no configuration values are returned.

- [ ] **Step 4: Update liveness/readiness endpoints**

`/health` remains 200 liveness. `/ready` returns 503 for overall `not_ready`; `degraded` returns 200 with `ready=True` and `status="degraded"`; fully healthy returns 200 `ready`.

- [ ] **Step 5: Verify focused tests**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_readiness.py tests/test_api_smoke.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add just-soundz-backend/app/services/readiness.py just-soundz-backend/app/main.py just-soundz-backend/tests/test_readiness.py just-soundz-backend/tests/test_api_smoke.py
git commit -m "feat: add structured backend readiness states"
```

### Task 6: Background failure finalization and Pass 1 evidence

**Files:**
- Modify: `just-soundz-backend/app/main.py`
- Modify: `just-soundz-backend/tests/test_jobs.py`
- Create: `docs/superpowers/verification/2026-09-06-core-backend-pass1.md`

**Interfaces:**
- Every `process_job` execution ends as `complete` or `failed`; instrumentation failures cannot strand a job in `running`.
- Verification matrix maps each Pass 1 acceptance criterion to exact code and test evidence.

- [ ] **Step 1: Add failing-background-job test**

```python
def test_process_job_failure_cannot_leave_running(monkeypatch):
    job = jobs.create(user_id="00000000-0000-0000-0000-000000000001")

    def explode(*args, **kwargs):
        raise RuntimeError("synthetic generation failure")

    monkeypatch.setattr(main_module, "run_generation", explode)
    main_module.process_job(
        job.id,
        main_module.GenerateRequest(prompt="original test beat"),
        user_id=job.user_id,
        request_id="req-test-failure",
    )
    updated = jobs.get(job.id)
    assert updated.status == "failed"
```

- [ ] **Step 2: Verify the test against current/hardened state**

Run: `cd just-soundz-backend && PYTHONPATH=. pytest -q tests/test_jobs.py`
Expected before any required fix: new failure-path assertions expose any stranded-state issue.

- [ ] **Step 3: Make terminal-store update the protected final action**

In the exception path, event publishing, usage tracking, and operational metrics are each best-effort. The job-state failure update must still execute if any of those secondary systems fail. On success, terminal `complete` writes follow the same idempotent state helper.

- [ ] **Step 4: Run full backend verification**

Run:
```bash
cd just-soundz-backend
python -m compileall -q app tests
PYTHONPATH=. pytest -q tests
```
Expected: both commands exit 0; pytest reports zero failures.

- [ ] **Step 5: Check new hardening code for unfinished placeholders and duplicate contracts**

Run:
```bash
git grep -nE 'TODO|TBD|implement later' -- just-soundz-backend/app/settings.py just-soundz-backend/app/errors.py just-soundz-backend/app/request_context.py just-soundz-backend/app/services/job_states.py || true
git grep -nE 'class (AppSettings|JobStateError|AppError|ReadinessChecker)' -- just-soundz-backend/app
```
Expected: no placeholder hits and one intended definition of each boundary class.

- [ ] **Step 6: Write completion evidence matrix**

Create `docs/superpowers/verification/2026-09-06-core-backend-pass1.md` with exactly these rows: startup/shutdown lifecycle, centralized critical settings, three-state dependency readiness, validated/idempotent job transitions, no stranded running jobs, request-ID propagation, stable error envelope, service health/readiness contract, generation compatibility, unit/API coverage. For every row record implementation files, tests, and verification status. A row is `PASS` only with code plus test evidence.

- [ ] **Step 7: Commit verification evidence**

```bash
git add just-soundz-backend/app just-soundz-backend/tests docs/superpowers/verification/2026-09-06-core-backend-pass1.md
git commit -m "test: verify core backend pass one completion"
```

- [ ] **Step 8: Require green GitHub Actions before merge**

Open the Pass 1 PR. `Just Maker Backend CI` must complete successfully on the final head commit. If it fails, diagnose the actual defect and fix it; do not weaken the accepted requirement or remove the failing regression test.
