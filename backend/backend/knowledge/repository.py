from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    KnowledgeChunkMetadata,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
)


async def create_document(
    session: AsyncSession,
    *,
    title: str,
    original_file_name: str,
    content_type: str,
    source: str,
    active: bool,
    created_by: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_dimensions: int,
    chroma_collection: str,
) -> tuple[KnowledgeDocument, KnowledgeDocumentVersion]:
    document = KnowledgeDocument(
        id=str(uuid4()),
        title=title,
        original_file_name=original_file_name,
        content_type=content_type,
        source=source,
        is_active=active,
        created_by=created_by,
    )
    version = KnowledgeDocumentVersion(
        id=str(uuid4()),
        document_id=document.id,
        version=1,
        status="processing",
        chunk_count=0,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_dimensions=embedding_dimensions,
        chroma_collection=chroma_collection,
    )
    session.add_all([document, version])
    await session.commit()
    return document, version


async def create_document_version(
    session: AsyncSession,
    *,
    document: KnowledgeDocument,
    title: str,
    original_file_name: str,
    content_type: str,
    source: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_dimensions: int,
    chroma_collection: str,
) -> KnowledgeDocumentVersion:
    document.title = title
    document.original_file_name = original_file_name
    document.content_type = content_type
    document.source = source
    document.updated_at = datetime.now(timezone.utc)
    next_version_number = max(version.version for version in document.versions) + 1
    version = KnowledgeDocumentVersion(
        id=str(uuid4()),
        document_id=document.id,
        version=next_version_number,
        status="processing",
        chunk_count=0,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_dimensions=embedding_dimensions,
        chroma_collection=chroma_collection,
    )
    session.add(version)
    await session.commit()
    await session.refresh(document, attribute_names=["versions"])
    return version


async def complete_version(
    session: AsyncSession,
    version: KnowledgeDocumentVersion,
    chunks: list[str],
) -> None:
    for index, content in enumerate(chunks):
        session.add(
            KnowledgeChunkMetadata(
                id=str(uuid4()),
                document_version_id=version.id,
                chunk_index=index,
                chroma_id=f"{version.id}:{index}",
                content_hash=sha256(content.encode()).hexdigest(),
            )
        )
    version.status = "completed"
    version.chunk_count = len(chunks)
    version.error_message = None
    await session.commit()


async def fail_version(
    session: AsyncSession,
    version: KnowledgeDocumentVersion,
    error_message: str,
) -> None:
    await session.rollback()
    await session.execute(
        update(KnowledgeDocumentVersion)
        .where(KnowledgeDocumentVersion.id == version.id)
        .values(status="failed", error_message=error_message[:512])
    )
    await session.commit()


async def list_documents(session: AsyncSession) -> list[KnowledgeDocument]:
    result = await session.scalars(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.deleted_at.is_(None))
        .options(
            selectinload(KnowledgeDocument.versions).selectinload(
                KnowledgeDocumentVersion.chunks
            )
        )
        .order_by(KnowledgeDocument.updated_at.desc())
    )
    return list(result.unique())


async def get_document(
    session: AsyncSession,
    document_id: str,
) -> KnowledgeDocument | None:
    return await session.scalar(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.deleted_at.is_(None),
        )
        .options(
            selectinload(KnowledgeDocument.versions).selectinload(
                KnowledgeDocumentVersion.chunks
            )
        )
    )


async def set_document_active(
    session: AsyncSession,
    document: KnowledgeDocument,
    active: bool,
) -> None:
    document.is_active = active
    document.updated_at = datetime.now(timezone.utc)
    await session.commit()


async def soft_delete_document(
    session: AsyncSession,
    document: KnowledgeDocument,
) -> None:
    now = datetime.now(timezone.utc)
    document.is_active = False
    document.deleted_at = now
    document.updated_at = now
    await session.commit()


def get_chroma_ids(document: KnowledgeDocument) -> list[str]:
    return [
        chunk.chroma_id
        for version in document.versions
        for chunk in version.chunks
    ]
