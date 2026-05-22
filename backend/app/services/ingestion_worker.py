import asyncio
import json
import ssl
from datetime import datetime
from typing import Optional
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.config import get_settings
from app.models.schemas import InferenceLog
from app.models.pydantic_models import InferenceLogPayload
from app.services.pii_redactor import pii_redactor


class IngestionWorker:
    """
    Background worker that consumes inference logs from Redis queue,
    validates/parses payloads, extracts metadata, and stores in PostgreSQL.
    """

    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.session_factory = None
        self.queue_key = self.settings.redis_queue_key
        self.running = False

    async def connect(self):
        self.redis_client = redis.from_url(self.settings.redis_url, decode_responses=True)
        # Mirror the same SSL/pool settings used by the main app engine
        if self.settings.serverless_mode or self.settings.database_ssl_require:
            _ssl_ctx = ssl.create_default_context()
            engine = create_async_engine(
                self.settings.database_url,
                echo=False,
                poolclass=NullPool,
                connect_args={"ssl": _ssl_ctx, "statement_cache_size": 0},
            )
        else:
            engine = create_async_engine(self.settings.database_url, echo=False)
        self.session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()

    async def process_log(self, log_json: str) -> bool:
        """Validate, parse, redact PII, and store a single log entry."""
        try:
            payload = InferenceLogPayload.model_validate_json(log_json)
        except Exception as e:
            print(f"[IngestionWorker] Invalid payload: {e}")
            return False

        # PII redaction on previews
        redacted_input = pii_redactor.redact(payload.input_preview)
        redacted_output = pii_redactor.redact(payload.output_preview)

        # Map to DB model
        log_entry = InferenceLog(
            id=payload.request_id,
            conversation_id=payload.conversation_id,
            request_id=payload.request_id,
            model=payload.model,
            provider=payload.provider,
            request_timestamp=payload.request_timestamp,
            response_timestamp=payload.response_timestamp,
            latency_ms=payload.latency_ms,
            input_tokens=payload.input_tokens,
            output_tokens=payload.output_tokens,
            total_tokens=payload.total_tokens,
            status=payload.status,
            error_message=payload.error_message,
            status_code=payload.status_code,
            input_preview=redacted_input,
            output_preview=redacted_output,
            is_streaming=payload.is_streaming,
            time_to_first_token_ms=payload.time_to_first_token_ms,
            extra_metadata=payload.metadata,
        )

        async with self.session_factory() as session:
            async with session.begin():
                session.add(log_entry)

        return True

    async def run(self):
        """Main loop: block-pop from Redis, process logs."""
        await self.connect()
        self.running = True
        print("[IngestionWorker] Started consuming from queue...")

        while self.running:
            try:
                # BRPOP blocks until an item is available (timeout 1s for graceful shutdown)
                result = await self.redis_client.brpop(self.queue_key, timeout=1)
                if result:
                    _, log_json = result
                    await self.process_log(log_json)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[IngestionWorker] Error processing: {e}")
                await asyncio.sleep(0.5)

        await self.disconnect()
        print("[IngestionWorker] Stopped.")

    def stop(self):
        self.running = False

    async def drain_queue(self, batch_size: int = 20) -> int:
        """
        Non-blocking queue drain — pops up to batch_size items and processes them.
        Used as a Starlette BackgroundTask in serverless mode (Vercel) so every
        API request opportunistically drains the queue without a dedicated worker.
        """
        if not self.redis_client or not self.session_factory:
            return 0
        processed = 0
        for _ in range(batch_size):
            try:
                log_json = await self.redis_client.rpop(self.queue_key)
                if log_json is None:
                    break
                await self.process_log(log_json)
                processed += 1
            except Exception as e:
                print(f"[IngestionWorker] drain_queue error: {e}")
                break
        return processed


ingestion_worker = IngestionWorker()
