# Pass 2 Security / Auth / Job Ownership Verification

Acceptance criteria are mapped to repository evidence below.

| Criterion | Implementation | Test evidence | Status |
|---|---|---|---|
| User-scoped job/retry/feedback/artifact/preference/memory/usage routes authenticate | app/main.py | tests/test_security_pass2.py::test_user_scoped_routes_require_authentication | PASS |
| Durable ownership with safe in-memory fallback | app/ownership.py | test_owned_job_uses_durable_store_when_configured; test_owned_job_in_memory_is_user_isolated | PASS |
| Cross-user access is 404-isolated | app/ownership.py, app/main.py | test_cross_user_in_memory_job_access_is_404 | PASS |
| Signed artifact URLs are ownership checked and bounded | app/services/artifact_delivery.py, app/main.py | test_signed_url_ttl_is_strictly_bounded | PASS |
| Public endpoints explicitly classified | app/security.py; docs/security/public-endpoints.md | repository inspection | PASS |
| Oversized prompt / malformed IDs / unsafe paths rejected | GenerateRequest, app/security.py | test_malformed_identifier_is_rejected; unsafe filename/path tests; existing GenerateRequest validation | PASS |
| Security headers and CORS explicit | app/security.py, app/settings.py, app/main.py | test_security_headers_are_attached; existing CORS/settings tests | PASS |
| Auth failures do not leak provider/token internals | app/services/auth.py, app/main.py | test_auth_provider_failure_does_not_leak_internal_details | PASS |
| Quota/concurrency enforcement tested | app/services/usage.py | test_concurrency_limit_blocks_authenticated_generation; existing usage tests | PASS |
| Security regression suite in normal CI | .github/workflows/just-maker-backend-ci.yml | Security contract job + test_security_pass2.py | PASS |

Repository/code-complete scope only. External identity, storage, and gateway services still require production provisioning/configuration.
