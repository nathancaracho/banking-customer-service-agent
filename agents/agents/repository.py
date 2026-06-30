from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models_db import Checkpoint


async def create_checkpoint(
    session: AsyncSession,
    request_id: str,
    chat_id: str,
    tool_name: str,
    parameters: dict[str, Any],
    auth_decision: dict[str, Any] | None = None,
    subject: dict[str, Any] | None = None,
    confirmation_text: str | None = None,
) -> Checkpoint:
    checkpoint = Checkpoint(
        id=str(uuid4()),
        request_id=request_id,
        chat_id=chat_id,
        tool_name=tool_name,
        parameters=parameters,
        status="pending",
        auth_decision=auth_decision,
        subject=subject,
        confirmation_text=confirmation_text,
    )
    session.add(checkpoint)
    await session.commit()
    await session.refresh(checkpoint)
    return checkpoint


async def get_checkpoint_by_id(
    session: AsyncSession,
    checkpoint_id: str,
) -> Checkpoint | None:
    result = await session.execute(
        select(Checkpoint).where(Checkpoint.id == checkpoint_id)
    )
    return result.scalar_one_or_none()


async def get_pending_checkpoint(
    session: AsyncSession,
    chat_id: str,
) -> Checkpoint | None:
    result = await session.execute(
        select(Checkpoint)
        .where(Checkpoint.chat_id == chat_id)
        .where(Checkpoint.status == "pending")
        .order_by(Checkpoint.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def mark_checkpoint_completed(
    session: AsyncSession,
    checkpoint: Checkpoint,
) -> None:
    checkpoint.status = "completed"
    await session.commit()


async def mark_checkpoint_failed(
    session: AsyncSession,
    checkpoint: Checkpoint,
) -> None:
    checkpoint.status = "failed"
    await session.commit()
