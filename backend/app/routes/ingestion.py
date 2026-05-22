from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional
import json
import redis.asyncio as redis

from app.models.database import get_db
from app.models.schemas import InferenceLog
from app.models.pydantic_models import InferenceLogPayload
from app.services.pii_redactor import pii_redactor
from app.config import get_settings

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


@router.post("/logs")
async def ingest_log(payload: InferenceLogPayload, db: AsyncSession = Depends(get_db)):
    """
    Direct HTTP ingestion endpoint.
    Alternative to Redis queue for simpler deployments or external SDK usage.
    Validates payload and stores in database.
    """
    # Validate required fields
    if not payload.request_id or not payload.conversation_id:
        raise HTTPException(status_code=400, detail="request_id and conversation_id are required")

    if not payload.model or not payload.provider:
        raise HTTPException(status_code=400, detail="model and provider are required")

    # Check for duplicate
    existing = await db.execute(
        select(InferenceLog).where(InferenceLog.request_id == payload.request_id)
    )
    if existing.scalar_one_or_none():
        return {"status": "duplicate", "request_id": payload.request_id}

    # Store
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
        input_preview=payload.input_preview,
        output_preview=payload.output_preview,
        is_streaming=payload.is_streaming,
        time_to_first_token_ms=payload.time_to_first_token_ms,
        extra_metadata=payload.metadata,
    )

    db.add(log_entry)
    await db.commit()

    return {"status": "ingested", "request_id": payload.request_id}


@router.post("/logs/batch")
async def ingest_logs_batch(payloads: list[InferenceLogPayload], db: AsyncSession = Depends(get_db)):
    """Batch ingest multiple log entries."""
    if len(payloads) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 logs per batch")

    results = []
    for payload in payloads:
        try:
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
                input_preview=payload.input_preview,
                output_preview=payload.output_preview,
                is_streaming=payload.is_streaming,
                time_to_first_token_ms=payload.time_to_first_token_ms,
                extra_metadata=payload.metadata,
            )
            db.add(log_entry)
            results.append({"request_id": payload.request_id, "status": "ingested"})
        except Exception as e:
            results.append({"request_id": payload.request_id, "status": "error", "error": str(e)})

    await db.commit()
    return {"results": results, "total": len(results)}


@router.get("/queue/status")
async def queue_status():
    """Get current queue depth."""
    settings = get_settings()
    try:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        depth = await r.llen(settings.redis_queue_key)
        await r.close()
        return {"queue_depth": depth}
    except Exception as e:
        return {"queue_depth": -1, "error": str(e)}


@router.post("/process-queue")
async def process_queue(
    batch_size: int = 50,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Drain the Redis inference-log queue and store entries in PostgreSQL.

    Used by Vercel Cron (runs every minute) when the background worker is disabled.
    Also callable manually for ops/debugging.
    Secured via CRON_SECRET env var when set.
    """
    settings = get_settings()

    # Validate cron secret when configured
    if settings.cron_secret:
        if authorization != f"Bearer {settings.cron_secret}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    processed = 0
    errors = 0

    try:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        for _ in range(min(batch_size, 200)):  # hard cap at 200 per call
            log_json = await r.rpop(settings.redis_queue_key)
            if log_json is None:
                break
            try:
                payload = InferenceLogPayload.model_validate_json(log_json)
                redacted_input = pii_redactor.redact(payload.input_preview)
                redacted_output = pii_redactor.redact(payload.output_preview)
                db.add(InferenceLog(
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
                ))
                processed += 1
            except Exception:
                errors += 1

        await db.commit()
        await r.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue processing failed: {e}")

    return {"processed": processed, "errors": errors}

