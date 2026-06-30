from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from .chroma_client import delete_chunks, update_chunks_active, upsert_chunks
from ..config import Settings
from .document_parser import InvalidDocumentError, parse_document
from .repository import (
    complete_version,
    create_document,
    create_document_version,
    fail_version,
    get_chroma_ids,
    set_document_active,
    soft_delete_document,
)
from .models import KnowledgeDocument, KnowledgeDocumentVersion
from .text_chunker import chunk_text


CHUNK_SIZE = 700
CHUNK_OVERLAP = 200
EMBEDDING_DIMENSIONS = 768


class KnowledgeIngestionError(RuntimeError):
    pass


async def ingest_document(
    session: AsyncSession,
    settings: Settings,
    *,
    content: bytes,
    file_name: str,
    content_type: str,
    title: str | None,
    source: str,
    active: bool,
    created_by: str,
) -> tuple[KnowledgeDocument, KnowledgeDocumentVersion]:
    document, version = await create_document(
        session,
        title=(title or Path(file_name).stem).strip(),
        original_file_name=file_name,
        content_type=content_type,
        source=source,
        active=active,
        created_by=created_by,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        embedding_dimensions=EMBEDDING_DIMENSIONS,
        chroma_collection=settings.chroma_collection,
    )
    chroma_ids: list[str] = []

    try:
        text = parse_document(content, content_type)
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        chroma_ids = [f"{version.id}:{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "document_id": document.id,
                "document_version_id": version.id,
                "chunk_index": index,
                "active": active,
                "source": source,
                "title": document.title,
            }
            for index in range(len(chunks))
        ]
        await upsert_chunks(
            settings.chroma_url,
            settings.chroma_collection,
            settings.litellm_url,
            settings.litellm_api_key,
            settings.embedding_model,
            EMBEDDING_DIMENSIONS,
            chroma_ids,
            chunks,
            metadatas,
        )
        await complete_version(session, version, chunks)
        return document, version
    except InvalidDocumentError:
        await fail_version(session, version, "Invalid document")
        raise
    except Exception as error:
        if chroma_ids:
            try:
                await delete_chunks(
                    settings.chroma_url,
                    settings.chroma_collection,
                    chroma_ids,
                )
            except Exception:
                pass
        await fail_version(session, version, "Knowledge ingestion failed")
        raise KnowledgeIngestionError("Knowledge ingestion failed") from error


async def reprocess_document(
    session: AsyncSession,
    settings: Settings,
    document: KnowledgeDocument,
    *,
    content: bytes,
    file_name: str,
    content_type: str,
    title: str | None,
    source: str | None,
) -> KnowledgeDocumentVersion:
    existing_ids = get_chroma_ids(document)
    version = await create_document_version(
        session,
        document=document,
        title=(title or Path(file_name).stem).strip(),
        original_file_name=file_name,
        content_type=content_type,
        source=source or document.source,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        embedding_dimensions=EMBEDDING_DIMENSIONS,
        chroma_collection=settings.chroma_collection,
    )
    new_chroma_ids: list[str] = []

    try:
        text = parse_document(content, content_type)
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        new_chroma_ids = [f"{version.id}:{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "document_id": document.id,
                "document_version_id": version.id,
                "chunk_index": index,
                "active": document.is_active,
                "source": document.source,
                "title": document.title,
            }
            for index in range(len(chunks))
        ]
        await update_chunks_active(
            settings.chroma_url,
            settings.chroma_collection,
            existing_ids,
            False,
        )
        await upsert_chunks(
            settings.chroma_url,
            settings.chroma_collection,
            settings.litellm_url,
            settings.litellm_api_key,
            settings.embedding_model,
            EMBEDDING_DIMENSIONS,
            new_chroma_ids,
            chunks,
            metadatas,
        )
        await complete_version(session, version, chunks)
        return version
    except InvalidDocumentError:
        await fail_version(session, version, "Invalid document")
        raise
    except Exception as error:
        if new_chroma_ids:
            try:
                await delete_chunks(
                    settings.chroma_url,
                    settings.chroma_collection,
                    new_chroma_ids,
                )
            except Exception:
                pass
        if existing_ids and document.is_active:
            try:
                await update_chunks_active(
                    settings.chroma_url,
                    settings.chroma_collection,
                    existing_ids,
                    True,
                )
            except Exception:
                pass
        await fail_version(session, version, "Knowledge ingestion failed")
        raise KnowledgeIngestionError("Knowledge ingestion failed") from error


async def change_document_status(
    session: AsyncSession,
    settings: Settings,
    document: KnowledgeDocument,
    active: bool,
) -> None:
    await update_chunks_active(
        settings.chroma_url,
        settings.chroma_collection,
        get_chroma_ids(document),
        active,
    )
    await set_document_active(session, document, active)


async def remove_document(
    session: AsyncSession,
    settings: Settings,
    document: KnowledgeDocument,
) -> None:
    await delete_chunks(
        settings.chroma_url,
        settings.chroma_collection,
        get_chroma_ids(document),
    )
    await soft_delete_document(session, document)
