import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.orm import relationship
from app.models.database import Base
import enum


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=True)
    status = Column(String(20), default=ConversationStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="conversation", order_by="ChatMessage.created_at")
    inference_logs = relationship("InferenceLog", back_populates="conversation")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    content_redacted = Column(Text, nullable=True)  # PII-redacted version
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class InferenceLog(Base):
    __tablename__ = "inference_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    request_id = Column(String(36), nullable=False, unique=True)

    # Provider info
    model = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)

    # Timing
    request_timestamp = Column(DateTime, nullable=False)
    response_timestamp = Column(DateTime, nullable=True)
    latency_ms = Column(Float, nullable=True)

    # Token usage
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), default="success")  # success, error, cancelled
    error_message = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)

    # Previews (truncated for storage)
    input_preview = Column(Text, nullable=True)
    output_preview = Column(Text, nullable=True)

    # Streaming
    is_streaming = Column(Boolean, default=False)
    time_to_first_token_ms = Column(Float, nullable=True)

    # Extra metadata
    extra_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="inference_logs")
