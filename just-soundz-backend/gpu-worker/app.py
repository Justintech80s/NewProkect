from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from worker import GPUWorker


app = FastAPI(title="Just Maker GPU Music Worker", version="1.0.0")
worker = GPUWorker()


class GeneratePayload(BaseModel):
    plan: Dict[str, Any]
    conditioning: Dict[str, Any] = {}
    variation: int = 0


def _authorize(authorization: str | None):
    expected = os.getenv("JUST_MAKER_GPU_WORKER_TOKEN")
    if not expected:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    supplied = authorization.split(" ", 1)[1].strip()
    if supplied != expected:
        raise HTTPException(status_code=403, detail="Invalid worker token")


@app.get("/health")
def health():
    return {
        "ok": True,
        "worker": worker.status(),
    }


@app.get("/capabilities")
def capabilities():
    return worker.capabilities()


@app.post("/generate")
def generate(
    payload: GeneratePayload,
    authorization: str | None = Header(default=None),
):
    _authorize(authorization)

    try:
        result = worker.generate(
            plan=payload.plan,
            conditioning=payload.conditioning,
            variation=payload.variation,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return result


@app.get("/artifacts/{filename}")
def artifact(
    filename: str,
    authorization: str | None = Header(default=None),
):
    _authorize(authorization)
    safe = Path(filename).name
    path = worker.output_dir / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path, media_type="audio/wav", filename=safe)
