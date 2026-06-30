from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import CurrentUser
from ..config import Settings
from .document_parser import InvalidDocumentError
from .repository import get_document, list_documents
from .schemas import (
    KnowledgeDocumentDetailResponse,
    KnowledgeDocumentResponse,
    KnowledgeIngestionResponse,
    KnowledgeStatusUpdate,
    KnowledgeVersionResponse,
)
from .service import (
    KnowledgeIngestionError,
    change_document_status,
    ingest_document,
    reprocess_document,
    remove_document,
)
from .models import KnowledgeDocument, KnowledgeDocumentVersion


_CONTENT_TYPES = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
}
_ADMIN_ROLES = {"manager", "admin"}


def create_knowledge_router(
    settings: Settings,
    get_current_user: Callable,
    get_session: Callable,
) -> APIRouter:
    router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])

    @router.post(
        "/documents",
        response_model=KnowledgeIngestionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def _upload_document(
        file: UploadFile = File(...),
        title: str | None = Form(default=None),
        source: str = Form(default="manual_upload"),
        active: bool = Form(default=True),
        current_user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> KnowledgeIngestionResponse:
        _require_admin(current_user)
        file_name = Path(file.filename or "").name
        content_type = _validate_file_type(file_name, file.content_type)
        content = await file.read(settings.kb_max_file_size_bytes + 1)

        if len(content) > settings.kb_max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File exceeds maximum size",
            )

        try:
            document, version = await ingest_document(
                session,
                settings,
                content=content,
                file_name=file_name,
                content_type=content_type,
                title=title,
                source=source,
                active=active,
                created_by=current_user.user_id,
            )
        except InvalidDocumentError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except KnowledgeIngestionError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

        return KnowledgeIngestionResponse(
            ingestion_id=version.id,
            document_id=document.id,
            status=version.status,
            chunk_size=version.chunk_size,
            chunk_overlap=version.chunk_overlap,
            embedding_dimensions=version.embedding_dimensions,
            chunk_count=version.chunk_count,
        )

    @router.get("/documents", response_model=list[KnowledgeDocumentResponse])
    async def _list_documents(
        current_user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> list[KnowledgeDocumentResponse]:
        _require_admin(current_user)
        return [_to_response(document) for document in await list_documents(session)]

    @router.get(
        "/documents/{document_id}",
        response_model=KnowledgeDocumentDetailResponse,
    )
    async def _get_document(
        document_id: str,
        current_user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> KnowledgeDocumentDetailResponse:
        _require_admin(current_user)
        document = await get_document(session, document_id)

        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return _to_detail_response(document)

    @router.patch(
        "/documents/{document_id}/status",
        response_model=KnowledgeDocumentDetailResponse,
    )
    async def _update_document_status(
        document_id: str,
        payload: KnowledgeStatusUpdate,
        current_user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> KnowledgeDocumentDetailResponse:
        _require_admin(current_user)
        document = await get_document(session, document_id)

        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        await change_document_status(session, settings, document, payload.active)
        return _to_detail_response(document)

    @router.post(
        "/documents/{document_id}/reprocess",
        response_model=KnowledgeIngestionResponse,
    )
    async def _reprocess_document(
        document_id: str,
        file: UploadFile = File(...),
        title: str | None = Form(default=None),
        source: str | None = Form(default=None),
        current_user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> KnowledgeIngestionResponse:
        _require_admin(current_user)
        document = await get_document(session, document_id)

        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        file_name = Path(file.filename or "").name
        content_type = _validate_file_type(file_name, file.content_type)
        content = await file.read(settings.kb_max_file_size_bytes + 1)

        if len(content) > settings.kb_max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File exceeds maximum size",
            )

        try:
            version = await reprocess_document(
                session,
                settings,
                document,
                content=content,
                file_name=file_name,
                content_type=content_type,
                title=title,
                source=source,
            )
        except InvalidDocumentError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except KnowledgeIngestionError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

        return KnowledgeIngestionResponse(
            ingestion_id=version.id,
            document_id=document.id,
            status=version.status,
            chunk_size=version.chunk_size,
            chunk_overlap=version.chunk_overlap,
            embedding_dimensions=version.embedding_dimensions,
            chunk_count=version.chunk_count,
        )

    @router.delete(
        "/documents/{document_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def _delete_document(
        document_id: str,
        current_user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> None:
        _require_admin(current_user)
        document = await get_document(session, document_id)

        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        await remove_document(session, settings, document)

    return router


def _require_admin(current_user: CurrentUser) -> None:
    if not _ADMIN_ROLES.intersection(current_user.roles):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _validate_file_type(file_name: str, provided_content_type: str | None) -> str:
    expected_content_type = _CONTENT_TYPES.get(Path(file_name).suffix.lower())

    if expected_content_type is None or provided_content_type != expected_content_type:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    return expected_content_type


def _latest_version(document: KnowledgeDocument) -> KnowledgeDocumentVersion:
    return max(document.versions, key=lambda version: version.version)


def _to_response(document: KnowledgeDocument) -> KnowledgeDocumentResponse:
    version = _latest_version(document)
    return KnowledgeDocumentResponse(
        document_id=document.id,
        title=document.title,
        original_file_name=document.original_file_name,
        content_type=document.content_type,
        source=document.source,
        active=document.is_active,
        status=version.status,
        active_version=version.version,
        chunk_count=version.chunk_count,
        embedding_dimensions=version.embedding_dimensions,
        updated_at=document.updated_at,
    )


def _to_detail_response(
    document: KnowledgeDocument,
) -> KnowledgeDocumentDetailResponse:
    response = _to_response(document)
    return KnowledgeDocumentDetailResponse(
        **response.model_dump(),
        versions=[
            KnowledgeVersionResponse(
                id=version.id,
                version=version.version,
                status=version.status,
                chunk_count=version.chunk_count,
                embedding_dimensions=version.embedding_dimensions,
                error_message=version.error_message,
                created_at=version.created_at,
            )
            for version in sorted(
                document.versions,
                key=lambda item: item.version,
                reverse=True,
            )
        ],
    )
