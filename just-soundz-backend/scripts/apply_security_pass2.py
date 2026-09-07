from pathlib import Path

path = Path("app/main.py")
text = path.read_text()

text = text.replace(
    "from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request\n",
    "from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request\n",
    1,
)
text = text.replace(
    "from .jobs import jobs\n",
    "from .jobs import jobs\nfrom .ownership import owned_job\nfrom .security import PUBLIC_ENDPOINTS, apply_security_headers, normalize_uuid\n",
    1,
)

# Security headers on every response.
anchor = '        if "response" in locals():\n            response.headers[REQUEST_ID_HEADER] = request_id\n'
replacement = '        if "response" in locals():\n            response.headers[REQUEST_ID_HEADER] = request_id\n            apply_security_headers(response)\n            if request.url.path.startswith("/v1/"):\n                response.headers.setdefault("Cache-Control", "no-store")\n'
if anchor not in text:
    raise SystemExit("request middleware anchor missing")
text = text.replace(anchor, replacement, 1)

# Generic authentication failures; never expose provider detail.
start = text.index("def require_user(")
end = text.index("\n\n\n@app.get(\"/ready\")", start)
old = text[start:end]
new = '''def require_user(authorization: Optional[str]) -> Dict[str, Any]:
    try:
        return user_auth.get_user(authorization)
    except PermissionError as exc:
        raise AppError(
            code="authentication_required",
            message="Authentication is required.",
            status_code=401,
            retryable=False,
        ) from exc
    except RuntimeError as exc:
        raise AppError(
            code="service_unavailable",
            message="Authentication service is temporarily unavailable.",
            status_code=503,
            retryable=True,
        ) from exc
'''
text = text[:start] + new + text[end:]

# Feedback ownership through common resolver.
old = '''    if not durable_jobs.get(job_id, user_id=user["id"]):
        raise HTTPException(status_code=404, detail="Job not found")
'''
new = '''    if not owned_job(
        job_id,
        user["id"],
        durable_store=durable_jobs,
        memory_store=jobs,
    ):
        raise HTTPException(status_code=404, detail="Job not found")
'''
if old not in text:
    raise SystemExit("feedback ownership anchor missing")
text = text.replace(old, new, 1)

# Retry: resolve ownership consistently, but durable persistence remains required.
old = '''    user = require_user(authorization)
    original = durable_jobs.get(job_id, user_id=user["id"])
    if not original:
        raise HTTPException(status_code=404, detail="Durable job not found")

    assessment = job_recovery.assess(original)
'''
new = '''    user = require_user(authorization)
    original = owned_job(
        job_id,
        user["id"],
        durable_store=durable_jobs,
        memory_store=jobs,
    )
    if not original:
        raise HTTPException(status_code=404, detail="Job not found")
    if not durable_jobs.configured:
        raise HTTPException(status_code=409, detail="retry_requires_durable_store")

    assessment = job_recovery.assess(original)
'''
if old not in text:
    raise SystemExit("retry ownership anchor missing")
text = text.replace(old, new, 1)

# Artifact endpoint path IDs and bounded expiry.
text = text.replace(
    "    expires_in: int = 900,\n",
    "    expires_in: int = Query(default=900, ge=60, le=3600),\n",
    1,
)
old = '''    user = require_user(authorization)
    if not durable_jobs.get(job_id, user_id=user["id"]):
        raise HTTPException(status_code=404, detail="Job not found")
    artifacts = durable_jobs.artifacts(job_id, user_id=user["id"])
    artifact = next((a for a in artifacts if a.get("id") == artifact_id), None)
'''
new = '''    user = require_user(authorization)
    try:
        normalized_job_id = normalize_uuid(job_id)
        normalized_artifact_id = normalize_uuid(artifact_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Artifact not found") from exc
    if not owned_job(
        normalized_job_id,
        user["id"],
        durable_store=durable_jobs,
        memory_store=jobs,
    ):
        raise HTTPException(status_code=404, detail="Job not found")
    artifacts = durable_jobs.artifacts(normalized_job_id, user_id=user["id"])
    artifact = next(
        (a for a in artifacts if a.get("id") == normalized_artifact_id),
        None,
    )
'''
if old not in text:
    raise SystemExit("artifact ownership anchor missing")
text = text.replace(old, new, 1)

# Job GET through common resolver.
old = '''    user = require_user(authorization)
    durable = durable_jobs.get(job_id, user_id=user["id"])
    if durable:
        durable["artifacts"] = durable_jobs.artifacts(job_id, user_id=user["id"])
        return durable

    job = jobs.get(job_id)
    if not job or job.user_id != user["id"]:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "stage": job.status,
        "progress": 1.0 if job.status == "complete" else 0.0,
        "result": job.result,
        "error": job.error,
        "artifacts": [],
    }
'''
new = '''    user = require_user(authorization)
    resolved = owned_job(
        job_id,
        user["id"],
        durable_store=durable_jobs,
        memory_store=jobs,
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Job not found")
    if durable_jobs.configured:
        resolved["artifacts"] = durable_jobs.artifacts(
            resolved["job_id"],
            user_id=user["id"],
        )
    return resolved
'''
if old not in text:
    raise SystemExit("get_job ownership anchor missing")
text = text.replace(old, new, 1)

path.write_text(text)
