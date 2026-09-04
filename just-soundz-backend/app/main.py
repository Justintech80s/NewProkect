import os
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from .jobs import jobs
from .services.analysis import AudioAnalyzer
from .services.arranger import ArrangementEngine
from .services.mastering import MasteringEngine
from .services.producer import ProducerPlanner
from .services.quality import QualityJudge
from .services.repetition import RepetitionDetector
from .services.router import GenerationRouter
from .services.section_repair import SectionRepairEngine
from .services.stems import StemSeparator

app = FastAPI(title="Just Soundz AI Backend", version="0.4.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "JUST_SOUNDZ_ALLOWED_ORIGINS",
        "https://just-soundz-ai-companion.justmarsh88.chatgpt.site",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

planner = ProducerPlanner()
arranger = ArrangementEngine()
router = GenerationRouter()
repetition_detector = RepetitionDetector()
repair_engine = SectionRepairEngine()
mastering = MasteringEngine()
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
    repetition: Dict[str, Any]
    mastering: Dict[str, Any]


def run_generation(req: GenerateRequest):
    plan = planner.build_plan(
        prompt=req.prompt,
        bpm=req.bpm,
        key=req.key,
        duration_seconds=req.duration_seconds,
    )
    plan = arranger.apply(plan)

    generation = router.generate(plan)
    if not generation.get("audio_path") and not generation.get("audio_url"):
        raise RuntimeError(generation.get("message", "No generator is configured."))

    repetition = {"score": 0.0, "too_repetitive": False, "reason": "remote_audio"}
    repair_attempts = 0

    if generation.get("audio_path"):
        repetition = repetition_detector.inspect(
            generation["audio_path"],
            section_count=max(2, min(8, len(plan.get("arrangement", [])))),
        )

        while repetition.get("too_repetitive") and repair_attempts < 2:
            repair_attempts += 1
            plan = repair_engine.repair_plan(plan, repetition, repair_attempts)
            candidate = router.generate(plan, variation=repair_attempts)
            if not candidate.get("audio_path"):
                break
            generation = candidate
            repetition = repetition_detector.inspect(
                generation["audio_path"],
                section_count=max(2, min(8, len(plan.get("arrangement", [])))),
            )

    mastering_result = {"mastered": False, "reason": "remote_audio"}
    if generation.get("audio_path"):
        mastering_result = mastering.process(generation["audio_path"])
        if mastering_result.get("mastered"):
            generation["unmastered_audio_path"] = generation["audio_path"]
            generation["audio_path"] = mastering_result["audio_path"]

    analysis_target = generation.get("audio_path")
    analysis = analyzer.analyze(analysis_target) if analysis_target else {
        "engine": "remote-output",
        "bpm": None,
        "key": None,
        "message": "Local analysis requires an accessible audio_path.",
    }

    score = quality.score(
        req.prompt,
        analysis_target or generation["audio_url"],
        analysis,
    )

    quality_attempts = 1
    while score["score"] < req.quality_threshold and quality_attempts < 3:
        candidate = router.generate(plan, variation=quality_attempts + repair_attempts)
        if not candidate.get("audio_path") and not candidate.get("audio_url"):
            break

        generation = candidate
        if generation.get("audio_path"):
            repetition = repetition_detector.inspect(
                generation["audio_path"],
                section_count=max(2, min(8, len(plan.get("arrangement", [])))),
            )
            mastering_result = mastering.process(generation["audio_path"])
            if mastering_result.get("mastered"):
                generation["unmastered_audio_path"] = generation["audio_path"]
                generation["audio_path"] = mastering_result["audio_path"]

        analysis_target = generation.get("audio_path")
        analysis = analyzer.analyze(analysis_target) if analysis_target else {
            "engine": "remote-output",
            "bpm": None,
            "key": None,
            "message": "Local analysis requires an accessible audio_path.",
        }
        score = quality.score(
            req.prompt,
            analysis_target or generation["audio_url"],
            analysis,
        )
        quality_attempts += 1

    stem_result = (
        stems.separate(generation["audio_path"])
        if req.make_stems and generation.get("audio_path")
        else {"enabled": False, "reason": "no local audio path or stems disabled"}
    )

    return {
        "plan": plan,
        "generation": {
            **generation,
            "attempts": quality_attempts,
            "repair_attempts": repair_attempts,
        },
        "analysis": analysis,
        "quality": score,
        "stems": stem_result,
        "repetition": repetition,
        "mastering": mastering_result,
    }


def process_job(job_id: str, req: GenerateRequest):
    jobs.update(job_id, status="running")
    try:
        result = run_generation(req)
        jobs.update(job_id, status="complete", result=result)
    except Exception as exc:
        jobs.update(job_id, status="failed", error=str(exc))


@app.get("/")
def root():
    return {
        "service": "Just Soundz AI Backend",
        "version": "0.4.0",
        "generator": router.provider,
        "status": "ready",
        "pipeline": [
            "producer",
            "arrangement",
            "generation",
            "repetition-check",
            "section-repair",
            "mastering",
            "quality-check",
            "stems",
        ],
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "just-soundz-ai-backend",
        "version": "0.4.0",
        "generator": router.provider,
    }


@app.post("/v1/render")
def render(req: GenerateRequest):
    """Return an immediately playable/downloadable mastered WAV response."""
    try:
        result = run_generation(req)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    path = result["generation"].get("audio_path")
    if not path:
        raise HTTPException(
            status_code=501,
            detail="The selected remote provider returned a URL instead of a local render.",
        )

    return FileResponse(
        path,
        media_type="audio/wav",
        filename="just-soundz-instrumental-mastered.wav",
        headers={
            "X-Just-Soundz-Provider": str(result["generation"].get("provider", "unknown")),
            "X-Just-Soundz-BPM": str(result["plan"].get("bpm", "")),
            "X-Just-Soundz-Key": str(result["plan"].get("key", "")),
            "X-Just-Soundz-Mastered": str(result["mastering"].get("mastered", False)).lower(),
        },
    )


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
