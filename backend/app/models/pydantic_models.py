from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


def _default_model() -> str:
    from app.config import get_settings
    return get_settings().default_model


def _default_provider() -> str:
    from app.config import get_settings
    return get_settings().default_provider


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    model: str = Field(default_factory=_default_model)
    provider: str = Field(default_factory=_default_provider)
    stream: bool = False


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []


class ConversationListItem(BaseModel):
    id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class InferenceLogPayload(BaseModel):
    request_id: str
    conversation_id: str
    model: str
    provider: str
    request_timestamp: datetime
    response_timestamp: Optional[datetime] = None
    latency_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    status: str = "success"
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    input_preview: Optional[str] = None
    output_preview: Optional[str] = None
    is_streaming: bool = False
    time_to_first_token_ms: Optional[float] = None
    metadata: Optional[dict] = None


class DashboardMetrics(BaseModel):
    total_requests: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_tokens: int
    error_rate: float
    requests_per_minute: float
    active_conversations: int


class LatencyBucket(BaseModel):
    timestamp: str
    avg_latency_ms: float
    request_count: int


class ErrorEntry(BaseModel):
    id: str
    conversation_id: str
    model: str
    provider: str
    error_message: str
    timestamp: datetime


class ProviderStats(BaseModel):
    provider: str
    model: str
    total_requests: int
    avg_latency_ms: float
    error_count: int
    total_tokens: int
