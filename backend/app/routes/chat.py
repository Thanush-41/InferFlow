import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import json

from app.models.database import get_db
from app.models.schemas import Conversation, ChatMessage, ConversationStatus
from app.models.pydantic_models import ChatRequest, ChatMessageResponse, ConversationResponse, ConversationListItem
from app.sdk.llm_wrapper import llm_wrapper
from app.services.pii_redactor import pii_redactor
from app.config import get_settings

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Context window: keep last N messages — controlled by MAX_CONTEXT_MESSAGES env var
MAX_CONTEXT_MESSAGES = get_settings().max_context_messages


@router.post("/send")
async def send_message(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Send a message and get a response (non-streaming)."""
    # Get or create conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation = Conversation(id=str(uuid.uuid4()), title=request.message[:50])
        db.add(conversation)
        await db.commit()
        conversation_id = conversation.id
    else:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.status == ConversationStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Conversation has been cancelled")

    # Store user message
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        content_redacted=pii_redactor.redact(request.message),
    )
    db.add(user_msg)
    await db.commit()

    # Build context from conversation history
    messages = await _build_context(db, conversation_id)

    # Call LLM
    response = await llm_wrapper.generate(
        messages=messages,
        model=request.model,
        provider=request.provider,
        conversation_id=conversation_id,
    )

    # Store assistant message
    assistant_msg = ChatMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=response.content,
        content_redacted=pii_redactor.redact(response.content),
    )
    db.add(assistant_msg)

    # Update conversation timestamp
    await db.execute(
        Conversation.__table__.update()
        .where(Conversation.id == conversation_id)
        .values(updated_at=datetime.utcnow())
    )
    await db.commit()

    return {
        "conversation_id": conversation_id,
        "message": ChatMessageResponse(
            id=assistant_msg.id,
            role="assistant",
            content=response.content,
            created_at=assistant_msg.created_at or datetime.utcnow(),
        ),
    }


@router.post("/send/stream")
async def send_message_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Send a message and get a streaming response."""
    # Get or create conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation = Conversation(id=str(uuid.uuid4()), title=request.message[:50])
        db.add(conversation)
        await db.commit()
        conversation_id = conversation.id
    else:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.status == ConversationStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Conversation has been cancelled")

    # Store user message
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        content_redacted=pii_redactor.redact(request.message),
    )
    db.add(user_msg)
    await db.commit()

    # Build context
    messages = await _build_context(db, conversation_id)

    async def stream_generator():
        full_response = []
        try:
            async for chunk in llm_wrapper.generate_stream(
                messages=messages,
                model=request.model,
                provider=request.provider,
                conversation_id=conversation_id,
            ):
                full_response.append(chunk)
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Store complete response
            content = "".join(full_response)
            assistant_msg = ChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                content_redacted=pii_redactor.redact(content),
            )
            async with db.begin():
                db.add(assistant_msg)

            yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-Id": conversation_id,
        },
    )


async def _build_context(db: AsyncSession, conversation_id: str) -> List[dict]:
    """Build conversation context from recent messages."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_CONTEXT_MESSAGES)
    )
    messages = result.scalars().all()
    messages.reverse()  # Chronological order

    return [{"role": msg.role, "content": msg.content} for msg in messages]
