"""
Vercel Python serverless entry point.

Vercel routes all /api/* and /health requests here via vercel.json rewrites.
mangum adapts the FastAPI ASGI app to AWS Lambda / Vercel's serverless runtime.
"""
import sys
import os

# Ensure the backend package is importable from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from mangum import Mangum
from app.main import app  # FastAPI ASGI application

# lifespan="off" — Vercel handles startup/shutdown differently from long-running servers.
# DB init (create_all) and Redis connect still happen via the first request's lifespan
# because we pass lifespan="auto" in production (mangum default).
handler = Mangum(app, lifespan="auto")
