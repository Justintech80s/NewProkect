import os
import time
import uuid
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
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
from .services.advanced_conditioning import AdvancedConditioningPlanner
from .services.analysis import AudioAnalyzer
from .services.artifacts import ArtifactManifest, ArtifactStore
from .services.artifact_delivery import SecureArtifactDelivery
from .services.auth import SupabaseUserAuth
from .services.arranger import ArrangementEngine
from .services.conditioning import ConditioningCompiler
from .services.candidate_ranker import CandidateRanker
from .services.candidate_budget import CandidateBudgetPlanner
from .services.creative_memory import CreativeMemoryStore
from .services.durable_jobs import DurableGenerationJobStore
from .services.evaluation import GenerationEvaluator
from .services.evaluation_store import EvaluationStore
from .services.event_bus import KafkaEventBus
from .services.job_recovery import JobRecoveryPlanner
from .services.harmony_planner import HarmonyPlanner
from .services.instrumentation_planner import InstrumentationPlanner
from .services.mastering import MasteringEngine
from .services.mastering_critic import MasteringCritic
from .services.mix_intelligence import MixIntelligence
from .services.novelty_engine import NoveltyEngine
from .services.producer import ProducerPlanner
from .services.producer_dna import ProducerDNAEngine
from .services.operations import OperationsMetrics, Stopwatch
from .services.originality_guard import OriginalityGuard
from .services.production_critic import ProductionCritic
from .services.preferences import PreferenceLearningStore
from .services.quality import QualityJudge
from .services.quality_cost_controller import QualityCostController
from .services.readiness import ReadinessChecker
from .services.reference_audio import ReferenceAudioAnalyzer
from .services.reference_traits import ReferenceTraitBlender
from .services.repetition import RepetitionDetector
from .services.rhythm_transformer import RhythmTransformer
from .services.router import GenerationRouter
from .services.sample_brain import SampleBrain
from .services.sample_processor import SampleProcessor
from .services.section_repair import SectionRepairEngine
from .services.self_repair import SelfRepairEngine
from .services.stem_arranger import StemArranger
from .services.stem_generator import ProfessionalStemGenerator
from .services.stem_mixer import StemMixer
from .services.stems import StemSeparator
from .services.usage import UsageQuotaService

app = FastAPI(title="Just Maker AI Backend", version="4.1.0")

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
advanced_conditioning = AdvancedConditioningPlanner()
artifact_manifest = ArtifactManifest()
artifact_store = ArtifactStore()
artifact_delivery = SecureArtifactDelivery()
user_auth = SupabaseUserAuth()
job_recovery = JobRecoveryPlanner()
durable_jobs = DurableGenerationJobStore()
generation_evaluator = GenerationEvaluator()
evaluation_store = EvaluationStore()
event_bus = KafkaEventBus()
conditioning_compiler = ConditioningCompiler()
candidate_ranker = CandidateRanker()
candidate_budget = CandidateBudgetPlanner()
creative_memory = CreativeMemoryStore()
production_critic = ProductionCritic()
preferences = PreferenceLearningStore()
stem_arranger = StemArranger()
professional_stems = ProfessionalStemGenerator()
stem_mixer = StemMixer()
producer_dna = ProducerDNAEngine()
reference_audio_analyzer = ReferenceAudioAnalyzer()
reference_trait_blender = ReferenceTraitBlender()
originality_guard = OriginalityGuard()
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
mastering_critic = MasteringCritic()
mix_intelligence = MixIntelligence()
novelty_engine = NoveltyEngine()
quality = QualityJudge()
stems = StemSeparator()
analyzer = AudioAnalyzer()
music_brain_search = MusicBrainSearch()
music_ingestion = MusicIngestionPipeline()
sample_rights = SampleRightsEngine()
dataset_ingestor = DatasetBatchIngestor()
music_context_builder = MusicBrainContextBuilder(music_brain_search)
usage_quota = UsageQuotaService()
operations = OperationsMetrics()
quality_cost_controller = QualityCostController(operations)
readiness = ReadinessChecker(
    database=music_brain_search.db,
    router=router,
    artifact_store=artifact_store,
    user_auth=user_auth,
)



@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    try:
        response = await call_next(request)
        success = response.status_code < 500
        return response
    finally:
        latency_ms = (time.perf_counter() - started) * 1000.0
        try:
            operations.record(
                "http_request",
                request_id=request_id,
                latency_ms=latency_ms,
                success=success if "success" in locals() else False,
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                },
            )
        except Exception:
            pass
        if "response" in locals():
            response.headers["X-Request-ID"] = request_id


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1200)
    duration_seconds: int = Field(default=120, ge=10, le=600)
    bpm: Optional[int] = Field(default=None, ge=40, le=240)
    key: Optional[str] = None
    make_stems: bool = True
    quality_threshold: float = Field(default=0.72, ge=0.0, le=1.0)
    reference_traits: Optional[Dict[str, float]] = None
    variation: int = Field(default=0, ge=0, le=5)
    candidate_count: int = Field(default=1, ge=1, le=3)
    candidate_mode: str = Field(default="manual", pattern="^(manual|adaptive)$")
    max_estimated_cost_usd: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class GenerateResponse(BaseModel):
    plan: Dict[str, Any]
    generation: Dict[str, Any]
    analysis: Dict[str, Any]
    quality: Dict[str, Any]
    stems: Dict[str, Any]
    repetition: Dict[str, Any]
    mastering: Dict[str, Any]
    production_critic: Dict[str, Any]
    evaluation: Dict[str, Any]


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    action: str = Field(pattern="^(like|dislike|save|reject)$")
    notes: Optional[str] = Field(default=None, max_length=500)


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


def generate_professional_stem_mix(plan: Dict[str, Any]) -> Dict[str, Any]:
    generated = []
    for index, request in enumerate(professional_stems.build_requests(plan)):
        stem_plan = request["plan"]
        stem_plan = advanced_conditioning.apply(stem_plan)
        stem_plan = conditioning_compiler.apply(stem_plan)

        result = router.generate(stem_plan, variation=100 + index)
        if result.get("audio_path"):
            generated.append({
                "stem": request["stem"],
                "audio_path": result["audio_path"],
                "provider": result.get("provider"),
                "routing": result.get("routing"),
            })

    raw_analysis = mix_intelligence.analyze_stems(generated)
    corrected_arrangement = mix_intelligence.apply_bus_corrections(
        plan.get("stem_arrangement") or {},
        raw_analysis,
    )
    mixed = stem_mixer.mix(
        generated,
        corrected_arrangement,
    )
    return {
        "requested": len(professional_stems.build_requests(plan)),
        "generated": generated,
        "mix_analysis": raw_analysis,
        "corrected_stem_arrangement": corrected_arrangement,
        "mix": mixed,
    }


def run_generation(req: GenerateRequest, user_id: str | None = None, _single_candidate: bool = False):
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

    if req.reference_traits:
        allowed_reference_traits = {
            "brightness",
            "low_end_weight",
            "rhythmic_density",
            "transient_punch",
            "dynamic_range",
            "mix_polish_hint",
        }
        cleaned_traits = {
            key: max(0.0, min(1.0, float(value)))
            for key, value in req.reference_traits.items()
            if key in allowed_reference_traits
        }
        plan["reference_audio"] = {
            "production_traits": cleaned_traits,
            "policy": {
                "melody_extracted": False,
                "note_sequence_stored": False,
                "production_traits_only": True,
            },
        }
        plan = reference_trait_blender.apply(plan)

    plan = originality_guard.apply(plan)
    plan = preferences.apply_to_plan(user_id, plan)
    plan = creative_memory.apply(user_id, plan)
    plan = novelty_engine.apply(plan, req.prompt, variation=req.variation)
    plan = rhythm_transformer.apply(plan)
    plan = harmony_planner.apply(plan)
    plan = instrumentation_planner.apply(plan)
    plan = sample_brain.apply(plan)
    plan = sample_processor.process_plan(plan)
    plan = arranger.apply(plan)
    plan = stem_arranger.apply(plan)
    plan = advanced_conditioning.apply(plan)
    plan = conditioning_compiler.apply(plan)

    professional_stem_result = {
        "enabled": bool(req.make_stems),
        "generated": [],
        "mix": {"mixed": False, "reason": "stems_disabled"},
    }

    if req.make_stems:
        professional_stem_result = {
            "enabled": True,
            **generate_professional_stem_mix(plan),
        }

    if (professional_stem_result.get("mix") or {}).get("mixed"):
        generation = {
            "provider": "professional-stem-mix",
            "audio_path": professional_stem_result["mix"]["audio_path"],
            "audio_url": None,
            "metadata": {
                "stem_count": professional_stem_result["mix"]["stem_count"],
                "stem_generation": True,
            },
        }
    else:
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
    mastering_review = {"pass": False, "issues": ["not_mastered"], "score": 0.0}
    mastering_corrections = 0
    if generation.get("audio_path"):
        mastering_result = mastering.process(generation["audio_path"])
        mastering_review = mastering_critic.evaluate(mastering_result)

        if not mastering_review.get("pass"):
            mastering_corrections += 1
            target_peak = mastering_critic.corrective_target_peak(mastering_review)
            mastering_result = mastering.process(
                generation["audio_path"],
                target_peak_db=target_peak,
            )
            mastering_review = mastering_critic.evaluate(mastering_result)

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
            plan = advanced_conditioning.apply(plan)
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
            mastering_review = mastering_critic.evaluate(mastering_result)
            if not mastering_review.get("pass"):
                mastering_corrections += 1
                target_peak = mastering_critic.corrective_target_peak(mastering_review)
                mastering_result = mastering.process(
                    generation["audio_path"],
                    target_peak_db=target_peak,
                )
                mastering_review = mastering_critic.evaluate(mastering_result)

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

    if req.make_stems and professional_stem_result.get("generated"):
        stem_result = {
            "enabled": True,
            "engine": "native-generated-stems",
            "generated": professional_stem_result.get("generated", []),
            "mix": professional_stem_result.get("mix", {}),
        }
    elif req.make_stems and generation.get("audio_path"):
        stem_result = stems.separate(generation["audio_path"])
    else:
        stem_result = {
            "enabled": False,
            "reason": "no local audio path or stems disabled",
        }

    evaluation = generation_evaluator.evaluate(
        plan=plan,
        generation=generation,
        analysis=analysis,
        quality=score,
        repetition=repetition,
        mastering={
            **mastering_result,
            "critic": mastering_review,
        },
        stems=stem_result,
        artifacts=[],
    )

    # Best-of-N mode generates a small candidate set, evaluates each through the
    # same full pipeline, then returns the strongest result. Recursive candidates
    # are forced to single-candidate mode to avoid nested fan-out.
    budget = candidate_budget.decide(
        requested_count=req.candidate_count,
        quality_threshold=req.quality_threshold,
        duration_seconds=req.duration_seconds,
        make_stems=req.make_stems,
        prompt=req.prompt,
        mode=req.candidate_mode,
    )

    cost_plan = quality_cost_controller.plan(
        duration_seconds=req.duration_seconds,
        candidate_count=budget["candidate_count"],
        make_stems=req.make_stems,
        max_estimated_cost_usd=req.max_estimated_cost_usd,
    )
    budget["candidate_count"] = cost_plan["candidate_count"]
    budget["cost_plan"] = cost_plan

    if budget["candidate_count"] > 1 and not _single_candidate:
        candidates = []
        for offset in range(budget["candidate_count"]):
            candidate_payload = req.model_dump()
            candidate_payload["candidate_count"] = 1
            candidate_payload["variation"] = (req.variation + offset) % 6
            candidate_req = GenerateRequest(**candidate_payload)
            candidate = run_generation(
                candidate_req,
                user_id=user_id,
                _single_candidate=True,
            )
            candidate["variation"] = candidate_req.variation
            candidates.append(candidate)

        ranked = candidate_ranker.rank(candidates)
        winner = dict(ranked[0]["candidate"])
        winner["candidate_selection"] = {
            "mode": "best-of-n",
            "candidate_count": len(candidates),
            "budget": budget,
            "selected_variation": ranked[0]["variation"],
            "ranking": candidate_ranker.summary(ranked),
        }
        return winner

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
        "mastering": {
            **mastering_result,
            "critic": mastering_review,
            "corrective_passes": mastering_corrections,
            "mix_analysis": professional_stem_result.get("mix_analysis", {}),
        },
        "production_critic": {
            **critique,
            "repair_instructions": production_critic.repair_instructions(critique),
        },
        "evaluation": evaluation,
    }


def process_job(job_id: str, req: GenerateRequest, user_id: str | None = None):
    jobs.update(job_id, status="running")
    event_bus.emit(
        os.getenv("JUST_MAKER_KAFKA_JOB_TOPIC", "justmaker.jobs"),
        "generation.started",
        {
            "job_id": job_id,
            "user_id": user_id,
            "duration_seconds": req.duration_seconds,
            "candidate_count": req.candidate_count,
            "make_stems": req.make_stems,
        },
        key=job_id,
    )
    request_id = str(uuid.uuid4())
    job_started = time.perf_counter()
    if user_id:
        usage_quota.record_event(
            user_id,
            "generation_started",
            job_id=job_id,
            metadata={"duration_seconds": req.duration_seconds},
        )
    durable_jobs.update(job_id, status="running", stage="planning", progress=0.05)

    try:
        durable_jobs.update(job_id, stage="generating", progress=0.20)
        result = run_generation(req, user_id=user_id)

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
            persisted = artifact_store.persist({
                **manifest,
                "user_id": user_id,
            })
            durable_jobs.save_artifact(persisted)
            artifacts.append(persisted)

        for stem in (result.get("stems") or {}).get("generated", []):
            stem_path = stem.get("audio_path")
            stem_name = stem.get("stem")
            if not stem_path or not stem_name:
                continue
            try:
                stem_manifest = artifact_manifest.from_path(
                    stem_path,
                    artifact_type=f"stem:{stem_name}",
                    job_id=job_id,
                    metadata={
                        "provider": stem.get("provider"),
                        "stem": stem_name,
                        "bpm": (result.get("plan") or {}).get("bpm"),
                        "key": (result.get("plan") or {}).get("key"),
                    },
                )
                stem_persisted = artifact_store.persist({
                    **stem_manifest,
                    "user_id": user_id,
                })
                durable_jobs.save_artifact(stem_persisted)
                artifacts.append(stem_persisted)
            except Exception:
                pass

        result["artifacts"] = artifacts
        generation_meta = result.get("generation") or {}
        estimated_cost = operations.estimate_generation_cost(
            req.duration_seconds,
            attempts=int(generation_meta.get("attempts") or 1),
            stem_count=max(1, len((result.get("stems") or {}).get("generated", [])) or 1),
        )
        result["operations"] = {
            "request_id": request_id,
            "estimated_cost_usd": estimated_cost,
        }
        result["evaluation"] = generation_evaluator.evaluate(
            plan=result.get("plan") or {},
            generation=result.get("generation") or {},
            analysis=result.get("analysis") or {},
            quality=result.get("quality") or {},
            repetition=result.get("repetition") or {},
            mastering=result.get("mastering") or {},
            stems=result.get("stems") or {},
            artifacts=artifacts,
        )
        evaluation_store.save(job_id, user_id, result["evaluation"])
        creative_memory.remember(user_id, job_id, result)
        operations.record(
            "generation_job",
            request_id=request_id,
            job_id=job_id,
            provider=(result.get("generation") or {}).get("provider"),
            latency_ms=(time.perf_counter() - job_started) * 1000.0,
            success=True,
            estimated_cost_usd=result["operations"]["estimated_cost_usd"],
            metadata={
                "duration_seconds": req.duration_seconds,
                "evaluation_score": (result.get("evaluation") or {}).get("score"),
            },
        )
        event_bus.emit(
            os.getenv("JUST_MAKER_KAFKA_JOB_TOPIC", "justmaker.jobs"),
            "generation.completed",
            {
                "job_id": job_id,
                "user_id": user_id,
                "provider": (result.get("generation") or {}).get("provider"),
                "evaluation_score": (result.get("evaluation") or {}).get("score"),
                "artifact_count": len(result.get("artifacts") or []),
                "estimated_cost_usd": (result.get("operations") or {}).get("estimated_cost_usd"),
            },
            key=job_id,
        )
        jobs.update(job_id, status="complete", result=result)
        if user_id:
            usage_quota.record_event(
                user_id,
                "generation_completed",
                job_id=job_id,
                metadata={
                    "duration_seconds": req.duration_seconds,
                    "provider": (result.get("generation") or {}).get("provider"),
                },
            )
        durable_jobs.update(
            job_id,
            status="complete",
            stage="complete",
            progress=1.0,
            result=result,
        )
    except Exception as exc:
        event_bus.emit(
            os.getenv("JUST_MAKER_KAFKA_JOB_TOPIC", "justmaker.jobs"),
            "generation.failed",
            {
                "job_id": job_id,
                "user_id": user_id,
                "error_type": exc.__class__.__name__,
            },
            key=job_id,
        )
        try:
            operations.record(
                "generation_job",
                request_id=request_id,
                job_id=job_id,
                latency_ms=(time.perf_counter() - job_started) * 1000.0,
                success=False,
                metadata={
                    "duration_seconds": req.duration_seconds,
                    "error_type": exc.__class__.__name__,
                },
            )
        except Exception:
            pass
        jobs.update(job_id, status="failed", error=str(exc))
        if user_id:
            usage_quota.record_event(
                user_id,
                "generation_failed",
                job_id=job_id,
                metadata={"error_type": exc.__class__.__name__},
            )
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
        "version": "4.1.0",
        "generator": router.provider,
        "status": "ready",
        "pipeline": [
            "music-brain-retrieval",
            "production-profile-retrieval",
            "relational-music-graph",
            "producer",
            "producer-dna",
            "reference-audio-intelligence",
            "reference-trait-blending",
            "originality-guard",
            "adaptive-preference-learning",
            "successful-generation-creative-memory",
            "controlled-novelty-engine",
            "multi-variation-generation-control",
            "best-of-n-candidate-selection",
            "adaptive-candidate-compute-budget",
            "quality-aware-cost-controller",
            "rhythm-transformer",
            "harmony-planner",
            "instrumentation-planner",
            "sample-brain",
            "sample-processing",
            "arrangement",
            "stem-arrangement",
            "advanced-audio-conditioning",
            "conditioning-compiler",
            "native-stem-generation",
            "stem-mixdown",
            "mix-intelligence",
            "adaptive-mastering",
            "mastering-critic",
            "capability-aware-worker-selection",
            "evaluation-driven-worker-routing",
            "contextual-worker-specialization-learning",
            "postgres-transactional-outbox",
            "kafka-event-backbone",
            "gpu-worker-event-consumer-ready",
            "gpu-model-worker",
            "generation",
            "repetition-check",
            "section-repair",
            "mastering",
            "quality-check",
            "production-critic",
            "automated-evaluation",
            "provider-benchmarking",
            "structured-operational-metrics",
            "worker-circuit-breakers",
            "readiness-checks",
            "cost-estimation",
            "closed-loop-self-repair",
            "stems",
            "durable-job-state",
            "artifact-persistence",
            "secure-signed-artifact-delivery",
            "job-recovery",
            "authenticated-user-ownership",
            "per-user-job-isolation",
            "usage-tracking",
            "quota-enforcement",
            "concurrency-limits",
            "abuse-protection",
        ],
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "just-maker-ai-backend",
        "version": "4.1.0",
        "generator": router.provider,
    }



def require_user(authorization: Optional[str]) -> Dict[str, Any]:
    try:
        return user_auth.get_user(authorization)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc



@app.get("/ready")
def ready():
    status = readiness.check()
    if not status["ready"]:
        raise HTTPException(status_code=503, detail=status)
    return status



@app.get("/v1/event-backbone")
def event_backbone_status(
    authorization: Optional[str] = Header(default=None),
):
    require_user(authorization)
    return {
        "postgres_outbox_configured": event_bus.outbox.configured,
        "kafka_configured": event_bus.configured,
        "job_topic": os.getenv("JUST_MAKER_KAFKA_JOB_TOPIC", "justmaker.jobs"),
        "gpu_request_topic": os.getenv(
            "JUST_MAKER_KAFKA_GPU_REQUEST_TOPIC",
            "justmaker.gpu.requests",
        ),
        "gpu_result_topic": os.getenv(
            "JUST_MAKER_KAFKA_GPU_RESULT_TOPIC",
            "justmaker.gpu.results",
        ),
        "rocksdb": {
            "enabled": False,
            "planned_role": "worker-side local cache",
        },
    }


@app.get("/v1/operations")
def operations_status(
    hours: int = 24,
    authorization: Optional[str] = Header(default=None),
):
    require_user(authorization)
    return {
        "readiness": readiness.check(),
        "metrics": operations.summary(max(1, min(hours, 168))),
        "worker_status": router.status(),
    }


@app.get("/v1/me")
def current_user(authorization: Optional[str] = Header(default=None)):
    return require_user(authorization)





@app.get("/v1/creative-memory")
def get_creative_memory(
    limit: int = 5,
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    return {
        "memories": creative_memory.best(user["id"], limit=limit),
        "policy": "broad-successful-production-recipes-only",
    }


@app.get("/v1/preferences")
def get_music_preferences(
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    return preferences.get_profile(user["id"])


@app.post("/v1/jobs/{job_id}/feedback")
def save_generation_feedback(
    job_id: str,
    req: FeedbackRequest,
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)

    if not durable_jobs.get(job_id, user_id=user["id"]):
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        return preferences.save_feedback(
            user_id=user["id"],
            job_id=job_id,
            rating=req.rating,
            action=req.action,
            notes=req.notes,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/usage")
def usage_status(authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    return usage_quota.status(user["id"])



@app.get("/v1/evaluations/providers")
def provider_evaluation_summary(
    authorization: Optional[str] = Header(default=None),
):
    require_user(authorization)
    return {
        "providers": evaluation_store.provider_summary(),
        "configured": evaluation_store.configured,
    }


@app.get("/v1/generation-workers")
def generation_workers():
    return router.status()


@app.get("/v1/music-brain/status")
def music_brain_status():
    return {
        "database_configured": music_brain_search.db.configured,
        "graph_configured": music_brain_search.graph.configured,
        "relational_graph_configured": music_brain_search.relational_graph.configured,
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
def create_job(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    quota = usage_quota.check(user["id"], req.duration_seconds)
    if not quota.get("allowed", False):
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Generation quota exceeded",
                "reasons": quota.get("reasons", []),
                "limits": quota.get("limits", {}),
                "usage": quota.get("usage", {}),
                "remaining": quota.get("remaining", {}),
            },
        )

    durable = durable_jobs.create(req.model_dump(), user_id=user["id"])

    if durable_jobs.configured:
        job_id = durable["job_id"]
        jobs.create_with_id(job_id, user_id=user["id"])
    else:
        job = jobs.create(user_id=user["id"])
        job_id = job.id

    usage_quota.record_event(
        user["id"],
        "generation_queued",
        job_id=job_id,
        metadata={"duration_seconds": req.duration_seconds},
    )
    event_bus.emit(
        os.getenv("JUST_MAKER_KAFKA_JOB_TOPIC", "justmaker.jobs"),
        "generation.queued",
        {
            "job_id": job_id,
            "user_id": user["id"],
            "request": req.model_dump(),
        },
        key=job_id,
    )
    background_tasks.add_task(process_job, job_id, req, user["id"])
    return {
        "job_id": job_id,
        "status": "queued",
        "durable": durable_jobs.configured,
    }


@app.post("/v1/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    original = durable_jobs.get(job_id, user_id=user["id"])
    if not original:
        raise HTTPException(status_code=404, detail="Durable job not found")

    assessment = job_recovery.assess(original)
    if not assessment["retryable"]:
        raise HTTPException(status_code=409, detail=assessment["reason"])

    request_payload = dict(original.get("request") or {})
    retry_seconds = int(request_payload.get("duration_seconds") or 120)
    quota = usage_quota.check(user["id"], retry_seconds)
    if not quota.get("allowed", False):
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Generation quota exceeded",
                "reasons": quota.get("reasons", []),
            },
        )

    try:
        req = GenerateRequest(**request_payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Stored request is invalid") from exc

    retry = durable_jobs.create(
        request_payload,
        retry_of=job_id,
        retry_count=int(original.get("retry_count") or 0) + 1,
        max_retries=int(original.get("max_retries") or 3),
        user_id=user["id"],
    )
    jobs.create_with_id(retry["job_id"], user_id=user["id"])
    background_tasks.add_task(process_job, retry["job_id"], req, user["id"])
    return {
        "job_id": retry["job_id"],
        "status": "queued",
        "retry_of": job_id,
        "retry_count": retry["retry_count"],
    }


@app.post("/v1/jobs/{job_id}/artifacts/{artifact_id}/signed-url")
def sign_job_artifact(
    job_id: str,
    artifact_id: str,
    expires_in: int = 900,
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    if not durable_jobs.get(job_id, user_id=user["id"]):
        raise HTTPException(status_code=404, detail="Job not found")
    artifacts = durable_jobs.artifacts(job_id, user_id=user["id"])
    artifact = next((a for a in artifacts if a.get("id") == artifact_id), None)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found for this job")

    bucket = artifact.get("bucket")
    object_path = artifact.get("object_path")
    if not bucket or not object_path:
        raise HTTPException(status_code=409, detail="Artifact is not persisted in private storage")

    try:
        return artifact_delivery.sign(
            bucket=bucket,
            object_path=object_path,
            expires_in=expires_in,
            download_name=artifact.get("filename"),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to create signed URL") from exc


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
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
