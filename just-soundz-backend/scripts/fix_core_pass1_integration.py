from pathlib import Path

path = Path("app/main.py")
text = path.read_text()

# The first integration patch intentionally transformed two matching RuntimeError
# blocks mechanically. Restore require_user to the service/auth category.
require_start = text.index("def require_user(")
require_end = text.index('\n\n\n@app.get("/ready")', require_start)
require_block = text[require_start:require_end]
wrong = '''    except RuntimeError as exc:\n        raise AppError(\n            code="generator_unavailable",\n            message="Music generation is temporarily unavailable.",\n            status_code=503,\n            retryable=True,\n        ) from exc\n'''
correct = '''    except RuntimeError as exc:\n        raise HTTPException(status_code=503, detail=str(exc)) from exc\n'''
if wrong not in require_block:
    raise SystemExit("expected transformed require_user RuntimeError block not found")
require_block = require_block.replace(wrong, correct, 1)
text = text[:require_start] + require_block + text[require_end:]

# Render should already be transformed by the first patch. Ensure generate is
# transformed explicitly and only within its function boundary.
generate_start = text.index('@app.post("/v1/generate"')
generate_end = text.index('\n\n@app.post("/v1/jobs")', generate_start)
generate_block = text[generate_start:generate_end]
old = '''    except RuntimeError as exc:\n        raise HTTPException(status_code=503, detail=str(exc)) from exc\n'''
new = '''    except RuntimeError as exc:\n        raise AppError(\n            code="generator_unavailable",\n            message="Music generation is temporarily unavailable.",\n            status_code=503,\n            retryable=True,\n        ) from exc\n'''
if old not in generate_block:
    raise SystemExit("expected generate RuntimeError block not found")
generate_block = generate_block.replace(old, new, 1)
text = text[:generate_start] + generate_block + text[generate_end:]

path.write_text(text)
