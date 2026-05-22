import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import init_db
from app.routes import chat, conversations, ingestion, dashboard
from app.services.ingestion_worker import ingestion_worker
from app.sdk.logger import inference_logger
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db()
    await inference_logger.connect()
    # Always connect the worker so drain_queue() is available for BackgroundTasks
    await ingestion_worker.connect()

    # Background worker: runs in Docker/long-lived processes.
    # On Vercel (serverless), disable it — queue is drained by BackgroundTask instead.
    worker_task = None
    if settings.background_worker_enabled:
        worker_task = asyncio.create_task(ingestion_worker.run())

    yield

    if worker_task:
        ingestion_worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    await ingestion_worker.disconnect()
    await inference_logger.disconnect()


app = FastAPI(
    title="LLM Inference Logger",
    description="Lightweight inference logging and ingestion system for LLM applications",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — origins controlled via CORS_ORIGINS env var
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(ingestion.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "llm-inference-logger"}
