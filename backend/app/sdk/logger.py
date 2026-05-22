import time
import uuid
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict
import redis.asyncio as redis
from app.config import get_settings
from app.models.pydantic_models import InferenceLogPayload


class InferenceLogger:
    """Lightweight logger that captures inference metadata and sends to ingestion pipeline via Redis."""

    def __init__(self):
        settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = settings.redis_url
        self.queue_key = settings.redis_queue_key
        self.preview_max_length = settings.preview_max_length

    async def connect(self):
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()

    def start_request(self, conversation_id: str, model: str, provider: str) -> Dict:
        """Start tracking a request. Returns context dict."""
        return {
            "request_id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "model": model,
            "provider": provider,
            "request_timestamp": datetime.utcnow(),
            "start_time": time.perf_counter(),
            "first_token_time": None,
        }

    def mark_first_token(self, context: Dict):
        """Mark time to first token for streaming responses."""
        if context.get("first_token_time") is None:
            context["first_token_time"] = time.perf_counter()

    async def end_request(
        self,
        context: Dict,
        status: str = "success",
        error_message: Optional[str] = None,
        status_code: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        input_preview: Optional[str] = None,
        output_preview: Optional[str] = None,
        is_streaming: bool = False,
        metadata: Optional[dict] = None,
    ):
        """End tracking and send log to ingestion queue."""
        end_time = time.perf_counter()
        latency_ms = (end_time - context["start_time"]) * 1000

        time_to_first_token_ms = None
        if context.get("first_token_time"):
            time_to_first_token_ms = (context["first_token_time"] - context["start_time"]) * 1000

        log = InferenceLogPayload(
            request_id=context["request_id"],
            conversation_id=context["conversation_id"],
            model=context["model"],
            provider=context["provider"],
            request_timestamp=context["request_timestamp"],
            response_timestamp=datetime.utcnow(),
            latency_ms=round(latency_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            status=status,
            error_message=error_message,
            status_code=status_code,
            input_preview=input_preview[:self.preview_max_length] if input_preview else None,
            output_preview=output_preview[:self.preview_max_length] if output_preview else None,
            is_streaming=is_streaming,
            time_to_first_token_ms=round(time_to_first_token_ms, 2) if time_to_first_token_ms else None,
            metadata=metadata,
        )

        # Send to Redis queue (fire-and-forget for near real-time)
        await self._enqueue_log(log)

    async def _enqueue_log(self, log: InferenceLogPayload):
        """Push log to Redis queue for async processing."""
        try:
            await self.connect()
            log_json = log.model_dump_json()
            await self.redis_client.lpush(self.queue_key, log_json)
        except Exception as e:
            # Log failures shouldn't break the main flow
            print(f"[InferenceLogger] Failed to enqueue log: {e}")


# Singleton
inference_logger = InferenceLogger()
