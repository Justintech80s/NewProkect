from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from .jobs import jobs
from .services.producer import ProducerPlanner
from .services.router import GenerationRouter
from .services.quality import QualityJudge
from .services.stems import StemSeparator
from .services.analysis import AudioAnalyzer

app = FastAPI(title="Just Soundz AI Backend", version="0.2.0")

planner = ProducerPlanner()
router = GenerationRouter()
quality = QualityJudge()
stems = StemSeparator()
analyzer = AudioAnalyzer()


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3)
    duration_seconds: int = Field(default=120, ge=10, le=600)
    bpm: Optional[int] = Field(default=None, ge=40, le=240)
    key: Optional[str] = None
    make_stems: bool = True
    quality_threshold: float = Field(default=0.72, ge=0.0, le=1.0)


class GenerateResponse(BaseModel):
    plan: Dict[str, Any]
    generation: Dict[str, Any]
    analysis: Dict[str, Any]
    quality: Dict[str, Any]
    stems: Dict[str, Any]


def run_generation(req: GenerateRequest):
    plan = planner.build_plan(
        prompt=req.prompt,
        bpm=req.bpm,
        key=req.key,
        duration_seconds=req.duration_seconds,
    )

    generation = router.generate(plan)

    if not generation.get("audio_path") and not generation.get("audio_url"):
        raise RuntimeError(generation.get("message", "No generator is configured."))

    analysis_target = generation.get("audio_path")
    analysis = analyzer.analyze(analysis_target) if analysis_target else {
        "engine": "remote-output",
        "bpm": None,
        "key": None,
        "message": "Local analysis requires an accessible audio_path.",
    }

    score = quality.score(req.prompt, analysis_target or generation["audio_url"], analysis)

    attempts = 1
    while score["score"] < req.quality_threshold and attempts < 3:
        candidate = router.generate(plan, variation=attempts)
        if not candidate.get("audio_path") and not candidate.get("audio_url"):
            break
        generation = candidate
        analysis_target = generation.get("audio_path")
        analysis = analyzer.analyze(analysis_target) if analysis_target else {
            "engine": "remote-output",
            "bpm": None,
            "key": None,
            "message": "Local analysis requires an accessible audio_path.",
        }
        score = quality.score(req.prompt, analysis_target or generation["audio_url"], analysis)
        attempts += 1

    stem_result = (
        stems.separate(generation["audio_path"])
        if req.make_stems and generation.get("audio_path")
        else {"enabled": False, "reason": "no local audio path or stems disabled"}
    )

    return {
        "plan": plan,
        "generation": {**generation, "attempts": attempts},
        "analysis": analysis,
        "quality": score,
        "stems": stem_result,
    }


def process_job(job_id: str, req: GenerateRequest):
    jobs.update(job_id, status="running")
    try:
        result = run_generation(req)
        jobs.update(job_id, status="complete", result=result)
    except Exception as exc:
        jobs.update(job_id, status="failed", error=str(exc))


@app.get("/health")
def health():
    return {"ok": True, "service": "just-soundz-ai-backend", "version": "0.2.0"}


@app.post("/v1/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    try:
        return run_generation(req)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/jobs")
def create_job(req: GenerateRequest, background_tasks: BackgroundTasks):
    job = jobs.create()
    background_tasks.add_task(process_job, job.id, req)
    return {"job_id": job.id, "status": job.status}


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "result": job.result,
        "error": job.error,
    }
