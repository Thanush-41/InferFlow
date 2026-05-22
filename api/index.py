"""
Vercel Python serverless entry point.

`handler` MUST be an unconditional top-level assignment — @vercel/python's
static analysis only recognises direct Module-level assignments.
lifespan="off" skips the async startup context; all service connections are
established lazily on first use.
"""
import sys
import os

_backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, _backend_path)

from fastapi import FastAPI
from mangum import Mangum

# Build the ASGI app; fall back to a diagnostic app if the backend can't be imported
# (`_app` is set before the unconditional `handler` assignment below).
try:
    from app.main import app as _app  # real FastAPI backend
except Exception as _exc:
    import traceback as _tb
    _err_detail = _tb.format_exc()
    print(f"[api/index.py] backend import error:\n{_err_detail}")

    _app = FastAPI()

    @_app.get("/{path:path}")
    def _err_route(path: str = ""):  # noqa: ANN001
        return {"error": "backend_import_failed", "detail": _err_detail}

# Unconditional top-level assignment — required by @vercel/python static analysis
handler = Mangum(_app, lifespan="off")
