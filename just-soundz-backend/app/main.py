import os
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from .jobs import jobs
from .music_brain.batch import DatasetBatchIngestor
from .music_brain.context import MusicBrainContextBuilder
from .music_brain.ingestion import MusicIngestionPipeline
from .music_brain.rights import SampleRightsEngine
from .music_brain.search import MusicBrainSearch
from .services.analysis import AudioAnalyzer
from .services.artifacts import ArtifactManifest, ArtifactStore
from .services.arranger import ArrangementEngine
from .services.conditioning import ConditioningCompiler
from .services.durable_jobs import DurableGenerationJobStore
from .services.harmony_planner import HarmonyPlanner
from .services.instrumentation_planner import InstrumentationPlanner
from .services.mastering import MasteringEngine
from .services.producer import ProducerPlanner
from .services.producer_dna import ProducerDNAEngine
from .services.production_critic import ProductionCritic
from .services.quality import QualityJudge
from .services.repetition import RepetitionDetector
from .services.rhythm_transformer import RhythmTransformer
from .services.router import GenerationRouter
from .services.sample_brain import SampleBrain
from .services.sample_processor import SampleProcessor
from .services.section_repair import SectionRepairEngine
from .services.self_repair import SelfRepairEngine
from .services.stem_arranger import StemArranger
from .services.stems import StemSeparator

app = FastAPI(title="Just Maker AI Backend", version="1.4.0")

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
artifact_manifest = ArtifactManifest()
artifact_store = ArtifactStore()
durable_jobs = DurableGenerationJobStore()
conditioning_compiler = ConditioningCompiler()
production_critic = ProductionCritic()
stem_arranger = StemArranger()
producer_dna = ProducerDNAEngine()
rhythm_transformer = RhythmTransformer()
harmony_planner = HarmonyPlanner()
instrumentation_planner = InstrumentationPlanner()
arranger = ArrangementEngine()
router = GenerationRouter()
sample_brain = SampleBrain()
sample_processor = SampleProcessor()
repetition_detector = RepetitionDetector()
repair_engine = SectionRepairEngine()
self_repair = SelfRepairEngine()
mastering = MasteringEngine()
quality = QualityJudge()
stems = StemSeparator()
analyzer = AudioAnalyzer()
music_brain_search = MusicBrainSearch()
music_ingestion = MusicIngestionPipeline()
sample_rights = SampleRightsEngine()
dataset_ingestor = DatasetBatchIngestor()
music_context_builder = MusicBrainContextBuilder(music_brain_search)


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
    production_critic: Dict[str, Any]


class MusicSearchRequest(BaseModel):
    query: str = Field(min_length=2)
    limit: int = Field(default=20, ge=1, le=100)
    sample_eligible_only: bool = False


class RightsCheckRequest(BaseModel):
    status: str
    source: Optional[str] = None
    license_name: Optional[str] = None
    commercial_use: bool = False
    sampling_allowed: bool = False


class MusicBrainzImportRequest(BaseModel):
    query: str = Field(min_length=2)
    max_records: int = Field(default=250, ge=1, le=5000)


def run_generation(req: GenerateRequest):
    music_context = music_context_builder.build(req.prompt)

    plan = planner.build_plan(
        prompt=req.prompt,
        bpm=req.bpm,
        key=req.key,
        duration_seconds=req.duration_seconds,
    )
    plan = music_context_builder.apply_to_plan(
        plan,
        music_context,
        user_bpm_supplied=req.bpm is not None,
        user_key_supplied=req.key is not None,
    )
    plan = producer_dna.apply(req.prompt, plan)
    plan = rhythm_transformer.apply(plan)
    plan = harmony_planner.apply(plan)
    plan = instrumentation_planner.apply(plan)
    plan = sample_brain.apply(plan)
    plan = sample_processor.process_plan(plan)
    plan = arranger.apply(plan)
    plan = stem_arranger.apply(plan)
    plan = conditioning_compiler.apply(plan)

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
    critique = production_critic.evaluate(
        plan,
        analysis,
        repetition,
        mastering_result,
    )

    quality_attempts = 1
    self_repair_attempts = 0
    while (
        (score["score"] < req.quality_threshold or not critique.get("pass", False))
        and quality_attempts < 3
    ):
        if not critique.get("pass", False):
            self_repair_attempts += 1
            plan = self_repair.apply(
                plan,
                critique,
                attempt=self_repair_attempts,
            )
            plan = stem_arranger.apply(plan)
            plan = conditioning_compiler.apply(plan)

        candidate = router.generate(
            plan,
            variation=quality_attempts + repair_attempts + self_repair_attempts,
        )
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
        critique = production_critic.evaluate(
            plan,
            analysis,
            repetition,
            mastering_result,
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
            "self_repair_attempts": self_repair_attempts,
        },
        "analysis": analysis,
        "quality": score,
        "stems": stem_result,
        "repetition": repetition,
        "mastering": mastering_result,
        "production_critic": {
            **critique,
            "repair_instructions": production_critic.repair_instructions(critique),
        },
    }


def process_job(job_id: str, req: GenerateRequest):
    jobs.update(job_id, status="running")
    durable_jobs.update(job_id, status="running", stage="planning", progress=0.05)

    try:
        durable_jobs.update(job_id, stage="generating", progress=0.20)
        result = run_generation(req)

        artifacts = []
        generation = result.get("generation") or {}
        master_path = generation.get("audio_path")
        if master_path:
            durable_jobs.update(job_id, stage="persisting-artifacts", progress=0.90)
            manifest = artifact_manifest.from_path(
                master_path,
                artifact_type="master",
                job_id=job_id,
                metadata={
                    "provider": generation.get("provider"),
                    "bpm": (result.get("plan") or {}).get("bpm"),
                    "key": (result.get("plan") or {}).get("key"),
                },
            )
            persisted = artifact_store.persist(manifest)
            durable_jobs.save_artifact(persisted)
            artifacts.append(persisted)

        result["artifacts"] = artifacts
        jobs.update(job_id, status="complete", result=result)
        durable_jobs.update(
            job_id,
            status="complete",
            stage="complete",
            progress=1.0,
            result=result,
        )
    except Exception as exc:
        jobs.update(job_id, status="failed", error=str(exc))
        durable_jobs.update(
            job_id,
            status="failed",
            stage="failed",
            error=str(exc),
        )


@app.get("/")
def root():
    return {
        "service": "Just Maker AI Backend",
        "version": "1.4.0",
        "generator": router.provider,
        "status": "ready",
        "pipeline": [
            "music-brain-retrieval",
            "producer",
            "producer-dna",
            "rhythm-transformer",
            "harmony-planner",
            "instrumentation-planner",
            "sample-brain",
            "sample-processing",
            "arrangement",
            "stem-arrangement",
            "conditioning-compiler",
            "capability-aware-worker-selection",
            "generation",
            "repetition-check",
            "section-repair",
            "mastering",
            "quality-check",
            "production-critic",
            "closed-loop-self-repair",
            "stems",
            "durable-job-state",
            "artifact-persistence",
        ],
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "just-maker-ai-backend",
        "version": "1.4.0",
        "generator": router.provider,
    }


@app.get("/v1/generation-workers")
def generation_workers():
    return router.status()


@app.get("/v1/music-brain/status")
def music_brain_status():
    return {
        "database_configured": music_brain_search.db.configured,
        "graph_configured": music_brain_search.graph.configured,
        "embedding_dimension": music_brain_search.embeddings.dimension,
        "sampling_policy": "rights-aware",
    }


@app.post("/v1/music-brain/search")
def search_music_brain(req: MusicSearchRequest):
    return music_brain_search.search(
        query=req.query,
        limit=req.limit,
        sample_eligible_only=req.sample_eligible_only,
    )


@app.post("/v1/music-brain/ingest")
def ingest_music_record(record: Dict[str, Any]):
    try:
        return music_ingestion.ingest(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/music-brain/rights/check")
def check_sample_rights(req: RightsCheckRequest):
    return sample_rights.evaluate(req.model_dump())


@app.post("/v1/music-brain/import/musicbrainz")
def import_musicbrainz(req: MusicBrainzImportRequest):
    if not dataset_ingestor.pipeline.db.configured:
        raise HTTPException(
            status_code=503,
            detail="JUST_MAKER_DATABASE_URL must be configured before persistent imports.",
        )
    return dataset_ingestor.ingest_musicbrainz_query(
        query=req.query,
        max_records=req.max_records,
    )


@app.get("/v1/music-brain/import/jobs/{job_id}")
def get_music_import_job(job_id: str):
    persistent = dataset_ingestor.database.get_ingestion_job(job_id)
    if persistent:
        return persistent

    checkpoint = dataset_ingestor.checkpoints.load(job_id)
    if checkpoint:
        return checkpoint

    raise HTTPException(status_code=404, detail="Import job not found")


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
    durable = durable_jobs.create(req.model_dump())

    if durable_jobs.configured:
        job_id = durable["job_id"]
        jobs.create_with_id(job_id)
    else:
        job = jobs.create()
        job_id = job.id

    background_tasks.add_task(process_job, job_id, req)
    return {
        "job_id": job_id,
        "status": "queued",
        "durable": durable_jobs.configured,
    }


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str):
    durable = durable_jobs.get(job_id)
    if durable:
        durable["artifacts"] = durable_jobs.artifacts(job_id)
        return durable

    job = jobs.get(job_id)
    if not job:
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
