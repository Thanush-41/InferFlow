"""
Vercel Python serverless entry point.

`handler` is an unconditional top-level assignment — @vercel/python's static
analysis requires this.  The backend package is bundled via includeFiles in
vercel.json so it is available at Lambda runtime.  lifespan="off" skips async
startup; all service connections are lazy.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from mangum import Mangum
from app.main import app  # FastAPI ASGI application

handler = Mangum(app, lifespan="off")
