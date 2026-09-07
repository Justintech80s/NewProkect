from pathlib import Path

path = Path("app/main.py")
text = path.read_text()

# Imports.
anchor = "from .jobs import jobs\n"
replacement = (
    "from .errors import AppError, register_error_handlers\n"
    "from .jobs import jobs\n"
    "from .request_context import REQUEST_ID_HEADER, normalize_request_id\n"
)
if anchor not in text:
    raise SystemExit("jobs import anchor missing")
text = text.replace(anchor, replacement, 1)

# Register error handlers after middleware configuration.
anchor = '''app.add_middleware(\n    CORSMiddleware,\n    allow_origins=settings.allowed_origins,\n    allow_credentials=False,\n    allow_methods=["GET", "POST", "OPTIONS"],\n    allow_headers=["*"],\n)\n\nplanner = ProducerPlanner()'''
replacement = '''app.add_middleware(\n    CORSMiddleware,\n    allow_origins=settings.allowed_origins,\n    allow_credentials=False,\n    allow_methods=["GET", "POST", "OPTIONS"],\n    allow_headers=["*"],\n)\nregister_error_handlers(app)\n\nplanner = ProducerPlanner()'''
if anchor not in text:
    raise SystemExit("middleware anchor missing")
text = text.replace(anchor, replacement, 1)

# Request ID middleware.
text = text.replace(
    '    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())\n    started = time.perf_counter()\n',
    '    request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))\n    request.state.request_id = request_id\n    started = time.perf_counter()\n',
    1,
)
text = text.replace(
    '            response.headers["X-Request-ID"] = request_id\n',
    '            response.headers[REQUEST_ID_HEADER] = request_id\n',
    1,
)

# Replace process_job prelude so every failure enters the protected finalizer.
start = text.index("def process_job(")
result_marker = text.index("        result = run_generation(req, user_id=user_id)\n", start)
new_prelude = '''def process_job(\n    job_id: str,\n    req: GenerateRequest,\n    user_id: str | None = None,\n    request_id: str | None = None,\n):\n    request_id = normalize_request_id(request_id)\n    job_started = time.perf_counter()\n    jobs.update(job_id, status="running", request_id=request_id)\n\n    try:\n        try:\n            event_bus.emit(\n                os.getenv("JUST_MAKER_KAFKA_JOB_TOPIC", "justmaker.jobs"),\n                "generation.started",\n                {\n                    "job_id": job_id,\n                    "request_id": request_id,\n                    "user_id": user_id,\n                    "duration_seconds": req.duration_seconds,\n                    "candidate_count": req.candidate_count,\n                    "make_stems": req.make_stems,\n                },\n                key=job_id,\n            )\n        except Exception:\n            pass\n\n        if user_id:\n            try:\n                usage_quota.record_event(\n                    user_id,\n                    "generation_started",\n                    job_id=job_id,\n                    metadata={"duration_seconds": req.duration_seconds},\n                )\n            except Exception:\n                pass\n\n        durable_jobs.update(\n            job_id,\n            status="running",\n            stage="planning",\n            progress=0.05,\n            request_id=request_id,\n        )\n        durable_jobs.update(job_id, stage="generating", progress=0.20)\n        result = run_generation(req, user_id=user_id)\n'''
text = text[:start] + new_prelude + text[result_marker + len("        result = run_generation(req, user_id=user_id)\n"):]

# Re-find the process block after replacement and replace its exception finalizer.
start = text.index("def process_job(")
end = text.index('\n\n@app.get("/")', start)
block = text[start:end]
exc = block.index("    except Exception as exc:")
block_prefix = block[:exc]
new_exception = '''    except Exception as exc:\n        # Secondary telemetry must never prevent the authoritative terminal write.\n        try:\n            event_bus.emit(\n                os.getenv("JUST_MAKER_KAFKA_JOB_TOPIC", "justmaker.jobs"),\n                "generation.failed",\n                {\n                    "job_id": job_id,\n                    "request_id": request_id,\n                    "user_id": user_id,\n                    "error_type": exc.__class__.__name__,\n                },\n                key=job_id,\n            )\n        except Exception:\n            pass\n        try:\n            operations.record(\n                "generation_job",\n                request_id=request_id,\n                job_id=job_id,\n                latency_ms=(time.perf_counter() - job_started) * 1000.0,\n                success=False,\n                metadata={\n                    "duration_seconds": req.duration_seconds,\n                    "error_type": exc.__class__.__name__,\n                },\n            )\n        except Exception:\n            pass\n        if user_id:\n            try:\n                usage_quota.record_event(\n                    user_id,\n                    "generation_failed",\n                    job_id=job_id,\n                    metadata={"error_type": exc.__class__.__name__},\n                )\n            except Exception:\n                pass\n        try:\n            durable_jobs.update(\n                job_id,\n                status="failed",\n                stage="failed",\n                error=str(exc),\n                request_id=request_id,\n            )\n        finally:\n            jobs.update(job_id, status="failed", error=str(exc), request_id=request_id)\n'''
block = block_prefix + new_exception
text = text[:start] + block + text[end:]

# Add request ID to completion event payload if not already present.
completion_anchor = '''            {\n                "job_id": job_id,\n                "user_id": user_id,\n                "provider": (result.get("generation") or {}).get("provider"),'''
completion_replacement = '''            {\n                "job_id": job_id,\n                "request_id": request_id,\n                "user_id": user_id,\n                "provider": (result.get("generation") or {}).get("provider"),'''
text = text.replace(completion_anchor, completion_replacement, 1)

# Readiness endpoint: degraded remains a successful readiness response.
old_ready = '''@app.get("/ready")\ndef ready():\n    status = readiness.check()\n    if not status["ready"]:\n        raise HTTPException(status_code=503, detail=status)\n    return status\n'''
new_ready = '''@app.get("/ready")\ndef ready():\n    status = readiness.check()\n    if status["status"] == "not_ready":\n        raise HTTPException(status_code=503, detail=status)\n    return status\n'''
if old_ready not in text:
    raise SystemExit("ready endpoint anchor missing")
text = text.replace(old_ready, new_ready, 1)

# Safe generation boundary errors.
text = text.replace(
    '    except RuntimeError as exc:\n        raise HTTPException(status_code=503, detail=str(exc)) from exc\n',
    '    except RuntimeError as exc:\n        raise AppError(\n            code="generator_unavailable",\n            message="Music generation is temporarily unavailable.",\n            status_code=503,\n            retryable=True,\n        ) from exc\n',
    2,
)

# Authenticated job creation now captures the HTTP request ID.
old_create_sig = '''def create_job(\n    req: GenerateRequest,\n    background_tasks: BackgroundTasks,\n    authorization: Optional[str] = Header(default=None),\n):'''
new_create_sig = '''def create_job(\n    req: GenerateRequest,\n    background_tasks: BackgroundTasks,\n    request: Request,\n    authorization: Optional[str] = Header(default=None),\n):'''
if old_create_sig not in text:
    raise SystemExit("create_job signature anchor missing")
text = text.replace(old_create_sig, new_create_sig, 1)
text = text.replace(
    '    durable = durable_jobs.create(req.model_dump(), user_id=user["id"])\n',
    '    request_id = request.state.request_id\n    durable = durable_jobs.create(\n        req.model_dump(), user_id=user["id"], request_id=request_id\n    )\n',
    1,
)
text = text.replace(
    '        jobs.create_with_id(job_id, user_id=user["id"])\n',
    '        jobs.create_with_id(job_id, user_id=user["id"], request_id=request_id)\n',
    1,
)
text = text.replace(
    '        job = jobs.create(user_id=user["id"])\n',
    '        job = jobs.create(user_id=user["id"], request_id=request_id)\n',
    1,
)
text = text.replace(
    '            "job_id": job_id,\n            "user_id": user["id"],\n            "request": req.model_dump(),\n',
    '            "job_id": job_id,\n            "request_id": request_id,\n            "user_id": user["id"],\n            "request": req.model_dump(),\n',
    1,
)
text = text.replace(
    '    background_tasks.add_task(process_job, job_id, req, user["id"])\n',
    '    background_tasks.add_task(process_job, job_id, req, user["id"], request_id)\n',
    1,
)

# Retry requests get their own trace ID while preserving retry lineage.
old_retry_sig = '''def retry_job(\n    job_id: str,\n    background_tasks: BackgroundTasks,\n    authorization: Optional[str] = Header(default=None),\n):'''
new_retry_sig = '''def retry_job(\n    job_id: str,\n    background_tasks: BackgroundTasks,\n    request: Request,\n    authorization: Optional[str] = Header(default=None),\n):'''
if old_retry_sig not in text:
    raise SystemExit("retry signature anchor missing")
text = text.replace(old_retry_sig, new_retry_sig, 1)
retry_create_anchor = '''        user_id=user["id"],\n    )\n    jobs.create_with_id(retry["job_id"], user_id=user["id"])\n    background_tasks.add_task(process_job, retry["job_id"], req, user["id"])'''
retry_create_replacement = '''        user_id=user["id"],\n        request_id=request.state.request_id,\n    )\n    jobs.create_with_id(\n        retry["job_id"],\n        user_id=user["id"],\n        request_id=request.state.request_id,\n    )\n    background_tasks.add_task(\n        process_job, retry["job_id"], req, user["id"], request.state.request_id\n    )'''
if retry_create_anchor not in text:
    raise SystemExit("retry creation anchor missing")
text = text.replace(retry_create_anchor, retry_create_replacement, 1)

path.write_text(text)
