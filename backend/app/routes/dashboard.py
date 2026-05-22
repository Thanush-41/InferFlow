from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta
from typing import List

from app.models.database import get_db
from app.models.schemas import InferenceLog, Conversation, ConversationStatus
from app.models.pydantic_models import DashboardMetrics, LatencyBucket, ErrorEntry, ProviderStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics(hours: int = 24, db: AsyncSession = Depends(get_db)):
    """Get aggregate dashboard metrics for the given time window."""
    since = datetime.utcnow() - timedelta(hours=hours)

    # Total requests
    total_result = await db.execute(
        select(func.count(InferenceLog.id)).where(InferenceLog.request_timestamp >= since)
    )
    total_requests = total_result.scalar() or 0

    # Average latency
    avg_result = await db.execute(
        select(func.avg(InferenceLog.latency_ms)).where(
            InferenceLog.request_timestamp >= since,
            InferenceLog.latency_ms.isnot(None)
        )
    )
    avg_latency = avg_result.scalar() or 0

    # P95 and P99 latency
    p95_result = await db.execute(
        text("""
            SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
            FROM inference_logs
            WHERE request_timestamp >= :since AND latency_ms IS NOT NULL
        """),
        {"since": since}
    )
    p95_latency = p95_result.scalar() or 0

    p99_result = await db.execute(
        text("""
            SELECT percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms)
            FROM inference_logs
            WHERE request_timestamp >= :since AND latency_ms IS NOT NULL
        """),
        {"since": since}
    )
    p99_latency = p99_result.scalar() or 0

    # Total tokens
    tokens_result = await db.execute(
        select(func.sum(InferenceLog.total_tokens)).where(InferenceLog.request_timestamp >= since)
    )
    total_tokens = tokens_result.scalar() or 0

    # Error rate
    error_result = await db.execute(
        select(func.count(InferenceLog.id)).where(
            InferenceLog.request_timestamp >= since,
            InferenceLog.status == "error"
        )
    )
    error_count = error_result.scalar() or 0
    error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0

    # Requests per minute
    minutes = hours * 60
    rpm = total_requests / minutes if minutes > 0 else 0

    # Active conversations
    active_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.status == ConversationStatus.ACTIVE)
    )
    active_conversations = active_result.scalar() or 0

    return DashboardMetrics(
        total_requests=total_requests,
        avg_latency_ms=round(avg_latency, 2),
        p95_latency_ms=round(p95_latency, 2),
        p99_latency_ms=round(p99_latency, 2),
        total_tokens=total_tokens,
        error_rate=round(error_rate, 2),
        requests_per_minute=round(rpm, 2),
        active_conversations=active_conversations,
    )


@router.get("/latency", response_model=List[LatencyBucket])
async def get_latency_timeseries(hours: int = 24, bucket_minutes: int = 5, db: AsyncSession = Depends(get_db)):
    """Get latency time series data bucketed by interval."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        text("""
            SELECT
                date_trunc('hour', request_timestamp) +
                (EXTRACT(minute FROM request_timestamp)::int / :bucket * interval '1 minute' * :bucket) as bucket,
                AVG(latency_ms) as avg_latency,
                COUNT(*) as request_count
            FROM inference_logs
            WHERE request_timestamp >= :since AND latency_ms IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket
        """),
        {"since": since, "bucket": bucket_minutes}
    )
    rows = result.fetchall()

    return [
        LatencyBucket(
            timestamp=row[0].isoformat() if row[0] else "",
            avg_latency_ms=round(row[1], 2),
            request_count=row[2],
        )
        for row in rows
    ]


@router.get("/errors", response_model=List[ErrorEntry])
async def get_errors(hours: int = 24, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get recent errors."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        select(InferenceLog)
        .where(InferenceLog.request_timestamp >= since, InferenceLog.status == "error")
        .order_by(InferenceLog.request_timestamp.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return [
        ErrorEntry(
            id=log.id,
            conversation_id=log.conversation_id,
            model=log.model,
            provider=log.provider,
            error_message=log.error_message or "Unknown error",
            timestamp=log.request_timestamp,
        )
        for log in logs
    ]


@router.get("/providers", response_model=List[ProviderStats])
async def get_provider_stats(hours: int = 24, db: AsyncSession = Depends(get_db)):
    """Get per-provider statistics."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        text("""
            SELECT
                provider,
                model,
                COUNT(*) as total_requests,
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                COALESCE(SUM(total_tokens), 0) as total_tokens
            FROM inference_logs
            WHERE request_timestamp >= :since
            GROUP BY provider, model
            ORDER BY total_requests DESC
        """),
        {"since": since}
    )
    rows = result.fetchall()

    return [
        ProviderStats(
            provider=row[0],
            model=row[1],
            total_requests=row[2],
            avg_latency_ms=round(row[3] or 0, 2),
            error_count=row[4],
            total_tokens=row[5],
        )
        for row in rows
    ]


@router.get("/throughput")
async def get_throughput(hours: int = 24, db: AsyncSession = Depends(get_db)):
    """Get throughput over time (requests per minute bucketed by 5-min intervals)."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await db.execute(
        text("""
            SELECT
                date_trunc('hour', request_timestamp) +
                (EXTRACT(minute FROM request_timestamp)::int / 5 * interval '5 minutes') as bucket,
                COUNT(*) as request_count,
                COALESCE(SUM(total_tokens), 0) as tokens
            FROM inference_logs
            WHERE request_timestamp >= :since
            GROUP BY bucket
            ORDER BY bucket
        """),
        {"since": since}
    )
    rows = result.fetchall()

    return [
        {
            "timestamp": row[0].isoformat() if row[0] else "",
            "requests": row[1],
            "tokens": row[2],
        }
        for row in rows
    ]
