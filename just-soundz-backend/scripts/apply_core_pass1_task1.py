from pathlib import Path

path = Path("app/main.py")
text = path.read_text()

old_import = "import os\nimport time\nimport uuid\n"
new_import = "import os\nimport time\nimport uuid\nfrom contextlib import asynccontextmanager\n"
if old_import not in text:
    raise SystemExit("expected import block not found")
text = text.replace(old_import, new_import, 1)

old_settings_import_anchor = "from .services.usage import UsageQuotaService\n\napp = FastAPI(title=\"Just Maker AI Backend\", version=\"5.2.0\")\n\nallowed_origins = [\n    origin.strip()\n    for origin in os.getenv(\n        \"JUST_SOUNDZ_ALLOWED_ORIGINS\",\n        \"https://just-soundz-ai-companion.justmarsh88.chatgpt.site\",\n    ).split(\",\")\n    if origin.strip()\n]\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=allowed_origins,\n    allow_credentials=False,\n    allow_methods=[\"GET\", \"POST\", \"OPTIONS\"],\n    allow_headers=[\"*\"],\n)\n"
new_settings_block = "from .services.usage import UsageQuotaService\nfrom .settings import get_settings, validate_startup\n\nsettings = get_settings()\n\n\n@asynccontextmanager\nasync def lifespan(app: FastAPI):\n    report = validate_startup(settings)\n    app.state.startup_report = report\n    if not report[\"valid\"]:\n        raise RuntimeError(\"invalid_startup_configuration\")\n    yield\n\n\napp = FastAPI(\n    title=\"Just Maker AI Backend\",\n    version=\"5.2.0\",\n    lifespan=lifespan,\n)\n\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=settings.allowed_origins,\n    allow_credentials=False,\n    allow_methods=[\"GET\", \"POST\", \"OPTIONS\"],\n    allow_headers=[\"*\"],\n)\n"
if old_settings_import_anchor not in text:
    raise SystemExit("expected FastAPI/CORS block not found")
text = text.replace(old_settings_import_anchor, new_settings_block, 1)

path.write_text(text)
