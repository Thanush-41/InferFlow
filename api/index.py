"""
Vercel Python serverless entry point.

handler must be a top-level unconditional assignment so Vercel's @vercel/python
runtime can detect it as a serverless function.  lifespan="off" skips the async
startup context; all service connections are established lazily on first use.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from mangum import Mangum
from app.main import app  # FastAPI ASGI application

# lifespan="off": FastAPI lifespan won't run on cold-start.
# Connections (DB, Redis) are made lazily on the first request.
handler = Mangum(app, lifespan="off")
