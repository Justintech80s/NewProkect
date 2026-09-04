from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from .services.producer import ProducerPlanner
from .services.router import GenerationRouter
from .services.quality import QualityJudge
from .services.stems import StemSeparator
from .services.analysis import AudioAnalyzer

app = FastAPI(title="Just Soundz AI Backend", version="0.1.0")

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

@app.get("/health")
def health():
    return {"ok": True, "service": "just-soundz-ai-backend"}

@app.post("/v1/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    plan = planner.build_plan(
        prompt=req.prompt,
        bpm=req.bpm,
        key=req.key,
        duration_seconds=req.duration_seconds,
    )

    generation = router.generate(plan)

    if not generation.get("audio_path"):
        raise HTTPException(status_code=503, detail=generation.get("message", "No generator is configured."))

    analysis = analyzer.analyze(generation["audio_path"])
    score = quality.score(req.prompt, generation["audio_path"], analysis)

    # Backend-only self-check: regenerate weak output without changing the UI contract.
    attempts = 1
    while score["score"] < req.quality_threshold and attempts < 3:
        generation = router.generate(plan, variation=attempts)
        if not generation.get("audio_path"):
            break
        analysis = analyzer.analyze(generation["audio_path"])
        score = quality.score(req.prompt, generation["audio_path"], analysis)
        attempts += 1

    stem_result = stems.separate(generation["audio_path"]) if req.make_stems else {"enabled": False}

    return {
        "plan": plan,
        "generation": {**generation, "attempts": attempts},
        "analysis": analysis,
        "quality": score,
        "stems": stem_result,
    }
