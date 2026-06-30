from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Chat, ChatSummary, Message


async def create_chat(session: AsyncSession, user_id: str) -> Chat:
    chat = Chat(id=str(uuid4()), user_id=user_id)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


async def list_chats(session: AsyncSession, user_id: str) -> list[Chat]:
    result = await session.scalars(
        select(Chat)
        .where(Chat.user_id == user_id)
        .order_by(Chat.updated_at.desc())
    )
    return list(result)


async def get_chat(
    session: AsyncSession,
    chat_id: str,
    user_id: str,
) -> Chat | None:
    return await session.scalar(
        select(Chat)
        .where(Chat.id == chat_id, Chat.user_id == user_id)
        .options(selectinload(Chat.messages), selectinload(Chat.summary))
    )


async def create_message(
    session: AsyncSession,
    chat: Chat,
    role: str,
    content: str,
    status: str,
) -> Message:
    message = Message(
        id=str(uuid4()),
        chat_id=chat.id,
        role=role,
        content=content,
        status=status,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def get_chat_memory(
    session: AsyncSession,
    chat_id: str,
    limit: int,
) -> tuple[ChatSummary | None, list[Message]]:
    summary = await session.get(ChatSummary, chat_id)
    
    stmt = select(Message).where(Message.chat_id == chat_id)
    
    if summary and summary.covered_until:
        stmt = stmt.where(Message.created_at > summary.covered_until)
        
    result = await session.scalars(
        stmt.order_by(Message.created_at.desc()).limit(limit)
    )
    return summary, list(reversed(list(result)))
