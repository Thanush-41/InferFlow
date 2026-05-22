"""
Vercel Python serverless entry point.
"""
import sys
import os
import traceback

# Ensure the backend package is importable from the project root
_backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, _backend_path)

_import_error: str | None = None

try:
    from mangum import Mangum
    from app.main import app  # FastAPI ASGI application
    handler = Mangum(app, lifespan="auto")
except Exception as _exc:
    _import_error = traceback.format_exc()
    print(f"[api/index.py] IMPORT ERROR:\n{_import_error}")

    # Fallback: return the traceback so the error is visible in Vercel logs/responses
    from fastapi import FastAPI as _FastAPI
    from mangum import Mangum as _Mangum

    _err_app = _FastAPI()

    @_err_app.get("/{path:path}")
    async def _error(path: str = ""):
        return {"error": "startup_import_failed", "detail": _import_error}

    handler = _Mangum(_err_app, lifespan="off")
