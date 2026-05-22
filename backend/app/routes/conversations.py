from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import List

from app.models.database import get_db
from app.models.schemas import Conversation, ChatMessage, ConversationStatus
from app.models.pydantic_models import ConversationResponse, ConversationListItem, ChatMessageResponse

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("/", response_model=List[ConversationListItem])
async def list_conversations(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all conversations with optional status filter."""
    query = select(Conversation).order_by(Conversation.updated_at.desc())

    if status:
        query = query.where(Conversation.status == status)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        # Get message count
        count_result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == conv.id)
        )
        msg_count = count_result.scalar() or 0

        items.append(ConversationListItem(
            id=conv.id,
            title=conv.title,
            status=conv.status,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=msg_count,
        ))

    return items


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get a conversation with all messages."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            ChatMessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )


@router.post("/{conversation_id}/cancel")
async def cancel_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel an active conversation."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.status == ConversationStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Conversation already cancelled")

    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(status=ConversationStatus.CANCELLED)
    )
    await db.commit()

    return {"status": "cancelled", "conversation_id": conversation_id}


@router.post("/{conversation_id}/resume")
async def resume_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Resume a cancelled conversation."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(status=ConversationStatus.ACTIVE)
    )
    await db.commit()

    return {"status": "active", "conversation_id": conversation_id}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete messages first
    await db.execute(
        ChatMessage.__table__.delete().where(ChatMessage.conversation_id == conversation_id)
    )
    await db.execute(
        Conversation.__table__.delete().where(Conversation.id == conversation_id)
    )
    await db.commit()

    return {"status": "deleted", "conversation_id": conversation_id}
