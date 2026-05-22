"""
Vercel Python serverless entry point — minimal smoke test.

If this works, we know Mangum+Vercel is compatible and the issue was
in the backend import chain.  If this also fails we need a different adapter.
"""
from fastapi import FastAPI
from mangum import Mangum

_app = FastAPI()


@_app.get("/health")
def _health():
    return {"status": "healthy", "note": "minimal smoke test"}


handler = Mangum(_app, lifespan="off")
